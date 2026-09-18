"""Elencos e escalações observados, sem inferir ausências ou efeitos estatísticos."""

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from sports_stats_analyzer.config import Settings
from sports_stats_analyzer.domain import Identifier, utc
from sports_stats_analyzer.providers.football_data import FootballDataClient, ProviderError
from sports_stats_analyzer.repository import connect
from sports_stats_analyzer.storage import save_snapshot


class Player(BaseModel):
    id: Identifier
    name: str = Field(min_length=1)
    position: str | None = None


def field_state(container: dict, key: str) -> str:
    if key not in container:
        return "missing"
    if container[key] is None:
        return "null"
    if not isinstance(container[key], list):
        return "invalid"
    return "present" if container[key] else "empty"


def player_list(container: dict, key: str) -> dict:
    state = field_state(container, key)
    if state != "present":
        return {"state": state, "players": []}
    try:
        players = [Player.model_validate(p).model_dump() for p in container[key]]
    except ValidationError:
        return {"state": "invalid", "players": []}
    if len({p["id"] for p in players}) != len(players):
        return {"state": "invalid", "players": []}
    return {"state": "present", "players": players}


def collect_detail(database: Path, resource: str, resource_id: int) -> dict:
    if resource not in {"match", "team", "person"} or resource_id < 1:
        raise ValueError("Recurso ou ID inválido")
    endpoint = (
        f"{ {'match': 'matches', 'team': 'teams', 'person': 'persons'}[resource] }/{resource_id}"
    )
    settings = Settings()
    try:
        with FootballDataClient(
            settings.football_data_api_token.get_secret_value(),
            settings.football_data_requests_per_minute,
        ) as client:
            payload = client.get(endpoint, unfold=resource == "match")
    except ProviderError as error:
        raise ValueError(str(error)) from None
    if payload.get("id") != resource_id:
        raise ValueError("Resposta não corresponde ao ID solicitado; coleta não salva")
    sid = save_snapshot(
        database, endpoint, {"_unfold": True} if resource == "match" else {}, payload
    )
    return {"snapshot_id": sid, "endpoint": endpoint, "database": str(database)}


def observations(database: Path, kind: str, before: datetime | None = None) -> list[dict]:
    cutoff = utc(before) if before is not None else None
    records = []
    with connect(database) as connection:
        snapshots = connection.execute("SELECT * FROM snapshots ORDER BY fetched_at, id").fetchall()
    for snapshot in snapshots:
        observed = utc(datetime.fromisoformat(snapshot["fetched_at"]))
        if snapshot["provider"] != "football-data.org" or (cutoff and observed > cutoff):
            continue
        parts = snapshot["endpoint"].strip("/").split("/")
        payload = json.loads(snapshot["payload_json"])
        if not isinstance(payload, dict):
            continue
        plural = {"match": "matches", "team": "teams", "person": "persons"}[kind]
        detail = len(parts) == 2 and parts[0] == plural and parts[1].isdigit()
        items = [payload] if detail else payload.get(plural, []) if parts[-1] == plural else []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict) or type(item.get("id")) is not int or item["id"] <= 0:
                continue
            records.append(
                {
                    "id": item["id"],
                    "snapshot_id": snapshot["id"],
                    "observed_at": observed.isoformat(),
                    "endpoint": snapshot["endpoint"],
                    "unfold_requested": json.loads(snapshot["params_json"]).get("_unfold", False),
                    "detail": detail,
                    "payload": item,
                }
            )
    return records


def evidence(observation: dict) -> dict:
    return {
        key: observation[key]
        for key in ("snapshot_id", "observed_at", "endpoint", "unfold_requested")
    }


def lineup(side: dict, status: str | None) -> dict:
    starters, bench = player_list(side, "lineup"), player_list(side, "bench")
    count = len(starters["players"])
    overlap = {p["id"] for p in starters["players"]} & {p["id"] for p in bench["players"]}
    state = (
        "invalid"
        if overlap or count > 11
        else ("reported_starting_xi" if count == 11 else "partial" if count else starters["state"])
    )
    return {
        "team_id": side.get("id"),
        "team_name": side.get("name"),
        "state": state,
        "starters": starters,
        "bench": bench,
        "formation": side.get("formation"),
        "confirmation": "not_independently_verified",
        "match_status": status,
    }


def side_data(payload: dict, side: str) -> dict:
    return payload[side] if isinstance(payload.get(side), dict) else {}


def match_context(database: Path, match_id: int, before: datetime) -> dict:
    before = utc(before)
    records = [r for r in observations(database, "match", before) if r["id"] == match_id]
    if not records:
        return {
            "match_id": match_id,
            "before": before.isoformat(),
            "state": "not_observed",
            "probability_adjustment": None,
        }
    detailed = [
        r
        for r in records
        if r["detail"]
        or r["unfold_requested"]
        or any("lineup" in side_data(r["payload"], side) for side in ("homeTeam", "awayTeam"))
    ]
    chosen = detailed[-1] if detailed else records[-1]
    payload, latest = chosen["payload"], records[-1]
    kickoff = payload.get("utcDate")
    try:
        kickoff_time = utc(datetime.fromisoformat(kickoff))
    except (ValueError, TypeError):
        kickoff_time = None
    sides = {
        key: lineup(side_data(payload, key), payload.get("status"))
        for key in ("homeTeam", "awayTeam")
    }
    for key, side in sides.items():
        side["first_observed_xi_at"] = None
        if side["state"] == "reported_starting_xi":
            ids = {p["id"] for p in side["starters"]["players"]}
            for record in records:
                previous = lineup(
                    side_data(record["payload"], key), record["payload"].get("status")
                )
                if (
                    previous["state"] == "reported_starting_xi"
                    and previous["team_id"] == side["team_id"]
                    and {p["id"] for p in previous["starters"]["players"]} == ids
                ):
                    side["first_observed_xi_at"] = record["observed_at"]
                    break
    return {
        "match_id": match_id,
        "before": before.isoformat(),
        "state": "observed",
        "evidence": evidence(chosen),
        "latest_match_evidence": evidence(latest),
        "latest_match_status": latest["payload"].get("status"),
        "kickoff": kickoff,
        "observed_before_kickoff": datetime.fromisoformat(chosen["observed_at"]) < kickoff_time
        if kickoff_time
        else None,
        "sides": sides,
        "events": {
            key: field_state(payload, key) for key in ("substitutions", "goals", "bookings")
        },
        "minutes": None,
        "per_90_metrics": None,
        "probability_adjustment": None,
        "warnings": [
            "Ausente, nulo ou vazio não prova ausência de atletas ou eventos.",
            "Onze jogadores informados não equivalem a confirmação independente.",
            "Formação não comprova tática; minutos e ajuste do modelo não são inferidos.",
            "Contexto detalhado e status recente podem vir de snapshots diferentes; confira horários.",
        ],
    }


def squad_context(database: Path, team_id: int, before: datetime) -> dict:
    before = utc(before)
    records = [r for r in observations(database, "team", before) if r["id"] == team_id]
    if not records:
        return {"team_id": team_id, "state": "not_observed", "before": before.isoformat()}
    chosen = records[-1]
    squad = player_list(chosen["payload"], "squad")
    return {
        "team_id": team_id,
        "before": before.isoformat(),
        "evidence": evidence(chosen),
        "state": "observed_squad",
        "squad": squad,
        "positions": dict(Counter(p["position"] or "unknown" for p in squad["players"])),
        "warnings": [
            "Elenco observado não é escalação, convocação ou prova de disponibilidade.",
            "A fonte pode listar participantes do elenco na temporada; não comprova vínculo atual.",
            "Não aplicar elenco atual a jogos históricos nem inferir transferências ou lesões.",
        ],
    }


def coverage(database: Path, competition: str | None = None, season: int | None = None) -> dict:
    groups = {}
    for record in observations(database, "match"):
        payload = record["payload"]
        comp, season_data = side_data(payload, "competition"), side_data(payload, "season")
        if competition is not None and competition.upper() not in (
            str(comp.get("id")),
            comp.get("code"),
        ):
            continue
        if season is not None and str(season_data.get("startDate", ""))[:4] != str(season):
            continue
        group = (
            "detail_or_unfolded"
            if record["detail"] or record["unfold_requested"]
            else "folded_list"
        )
        groups.setdefault(group, []).append(record)
    reports = {}
    for group, samples in groups.items():
        fields = {
            f"{side}.{field}": dict(
                Counter(player_list(side_data(r["payload"], side), field)["state"] for r in samples)
            )
            for side in ("homeTeam", "awayTeam")
            for field in ("lineup", "bench")
        }
        fields.update(
            {
                field: dict(Counter(field_state(r["payload"], field) for r in samples))
                for field in ("substitutions", "goals", "bookings")
            }
        )
        reports[group] = {
            "observations": len(samples),
            "distinct_matches": len({r["id"] for r in samples}),
            "fields": fields,
            "snapshot_ids": sorted({r["snapshot_id"] for r in samples}),
        }
    return {
        "competition": competition,
        "season": season,
        "match_observations": reports,
        "team_detail_observations_all_scopes": sum(
            r["detail"] for r in observations(database, "team")
        ),
        "person_observations_all_scopes": len(observations(database, "person")),
        "model_context_enabled": False,
        "model_context_reason": "Player effect and minutes models are not implemented or validated.",
        "warnings": [
            "Auditoria da amostra, não garantia sobre o plano ou todas as competições.",
            "Lista dobrada não comprova falta de cobertura; confira detalhe/expansão.",
            "Campos vazios não comprovam zero eventos. Minutos e impacto de jogadores indisponíveis.",
        ],
    }


def player_context(database: Path, player_id: int, before: datetime) -> dict:
    before = utc(before)
    records = [r for r in observations(database, "person", before) if r["id"] == player_id]
    if not records:
        return {"player_id": player_id, "before": before.isoformat(), "state": "not_observed"}
    chosen = records[-1]
    player = Player.model_validate(chosen["payload"])
    team = side_data(chosen["payload"], "currentTeam")
    return {
        "player_id": player_id,
        "before": before.isoformat(),
        "state": "observed_profile",
        "profile": player.model_dump(),
        "evidence": evidence(chosen),
        "reported_team": {"id": team.get("id"), "name": team.get("name")},
        "minutes": None,
        "per_90_metrics": None,
        "probability_adjustment": None,
        "warnings": [
            "Perfil e vínculo informados na observação; não demonstram disponibilidade para uma partida.",
            "Sem minutos ou eventos individuais suficientes, não há métricas de desempenho.",
        ],
    }
