"""Vincula eventos confirmados manualmente a partidas locais e importa odds recentes."""

from datetime import datetime, timedelta

from pydantic import ValidationError

from sports_stats_analyzer.domain import utc
from sports_stats_analyzer.markets import QUOTE_TTL, Quote, current_match, import_quotes, now
from sports_stats_analyzer.providers.the_odds_api import SPORT, OddsAPIError, TheOddsAPIClient

KICKOFF_TOLERANCE = timedelta(hours=2)


def _local_match(database, match_id: int) -> dict:
    match = current_match(database, match_id, now())
    if match["competition_code"] != "BSA":
        raise ValueError("Coleta de odds disponível somente para BSA.")
    if (
        match["status"] not in {"SCHEDULED", "TIMED"}
        or utc(datetime.fromisoformat(match["kickoff_at"])) <= now()
    ):
        raise ValueError("Coleta de odds exige partida local ainda não iniciada.")
    return match


def _event_time(event: dict) -> datetime | None:
    try:
        return utc(datetime.fromisoformat(event["commence_time"]))
    except (KeyError, TypeError, ValueError):
        return None


def _match_summary(match: dict) -> dict:
    return {
        "match_id": match["external_id"],
        "kickoff": match["kickoff_at"],
        "home_team": match["home_name"],
        "away_team": match["away_name"],
    }


def event_candidates(database, client: TheOddsAPIClient, match_id: int) -> dict:
    """Lista jogos próximos ao horário local, sem inferir identidade pelos nomes."""
    match = _local_match(database, match_id)
    kickoff = utc(datetime.fromisoformat(match["kickoff_at"]))
    candidates = []
    for event in client.events():
        event_time = _event_time(event)
        if (
            event.get("sport_key") != SPORT
            or event_time is None
            or abs(event_time - kickoff) > KICKOFF_TOLERANCE
            or not all(
                isinstance(event.get(key), str) and event[key]
                for key in ("id", "home_team", "away_team")
            )
        ):
            continue
        candidates.append(
            {
                "event_id": event["id"],
                "kickoff": event_time.isoformat(),
                "home_team": event["home_team"],
                "away_team": event["away_team"],
            }
        )
    return {
        "local_match": _match_summary(match),
        "candidates": candidates,
        "instruction": "Confira mandante, visitante e horário antes de importar um event_id.",
    }


def import_event_odds(
    database,
    client: TheOddsAPIClient,
    match_id: int,
    event_id: str,
    *,
    region: str = "eu",
    confirmed: bool = False,
    bookmaker: str | None = None,
) -> dict:
    """Importa apenas 1X2 completo e recente de um evento confirmado pelo usuário."""
    if not confirmed:
        raise ValueError("Confira o evento em odds-events e use --confirm-match para importar.")
    match = _local_match(database, match_id)
    event = client.event_odds(event_id, region)
    event_time = _event_time(event)
    if (
        event.get("id") != event_id
        or event.get("sport_key") != SPORT
        or event_time is None
        or abs(event_time - utc(datetime.fromisoformat(match["kickoff_at"]))) > KICKOFF_TOLERANCE
        or not all(
            isinstance(event.get(key), str) and event[key] for key in ("home_team", "away_team")
        )
        or event["home_team"] == event["away_team"]
    ):
        raise ValueError("Evento não corresponde à competição ou ao horário da partida local.")
    collected = now()
    quotes = []
    skipped_stale = skipped_incomplete = 0
    books = event.get("bookmakers")
    if not isinstance(books, list):
        raise OddsAPIError("Resposta da The Odds API sem lista de casas válida.")
    for book in books:
        if not isinstance(book, dict) or not isinstance(book.get("key"), str) or not book["key"]:
            skipped_incomplete += 1
            continue
        if bookmaker is not None and book["key"] != bookmaker:
            continue
        markets = book.get("markets")
        if not isinstance(markets, list):
            skipped_incomplete += 1
            continue
        h2h = next(
            (item for item in markets if isinstance(item, dict) and item.get("key") == "h2h"), None
        )
        if h2h is None:
            skipped_incomplete += 1
            continue
        try:
            updated = utc(datetime.fromisoformat(h2h.get("last_update") or book["last_update"]))
        except (KeyError, TypeError, ValueError):
            skipped_incomplete += 1
            continue
        if not timedelta(0) <= collected - updated <= QUOTE_TTL:
            skipped_stale += 1
            continue
        outcomes = h2h.get("outcomes")
        if not isinstance(outcomes, list) or len(outcomes) != 3:
            skipped_incomplete += 1
            continue
        names = {event["home_team"]: "home", "Draw": "draw", event["away_team"]: "away"}
        if any(
            not isinstance(item, dict) or not isinstance(item.get("name"), str) for item in outcomes
        ):
            skipped_incomplete += 1
            continue
        if {item["name"] for item in outcomes} != set(names):
            skipped_incomplete += 1
            continue
        try:
            batch = [
                Quote.model_validate(
                    {
                        "match_id": match_id,
                        "market": "1x2",
                        "selection": names[outcome["name"]],
                        "line": None,
                        "odds": outcome["price"],
                        "bookmaker": book["key"],
                        "observed_at": updated,
                        "source": f"the-odds-api:v4:{event_id}:{book['key']}:h2h",
                    }
                )
                for outcome in outcomes
            ]
        except (KeyError, TypeError, ValueError, ValidationError):
            skipped_incomplete += 1
            continue
        quotes.extend(batch)
    result = (
        import_quotes(database, quotes)
        if quotes
        else {"inserted": 0, "duplicates": 0, "quote_ids": []}
    )
    return {
        "local_match": _match_summary(match),
        "provider_event": {
            "event_id": event_id,
            "kickoff": event_time.isoformat(),
            "home_team": event["home_team"],
            "away_team": event["away_team"],
        },
        "region": region,
        "skipped_stale_bookmakers": skipped_stale,
        "skipped_incomplete_bookmakers": skipped_incomplete,
        **result,
    }
