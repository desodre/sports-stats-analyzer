"""Candidatos de vínculo CBF ↔ football-data.org com evidência de partidas."""

import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def _match_time(value: str) -> datetime:
    return datetime.strptime(value, "%d/%m/%Y - %H:%M").replace(tzinfo=SAO_PAULO)


def _report(teams: list[dict], cbf_games: list[dict], fd_games: list[dict], season: int) -> dict:
    by_exact: dict[tuple, list[dict]] = defaultdict(list)
    by_date_score: dict[tuple, list[dict]] = defaultdict(list)
    names = {}
    for game in fd_games:
        kickoff = datetime.fromisoformat(game["kickoff_at"])
        if kickoff.tzinfo is None:
            raise ValueError("Horário football-data.org sem fuso horário")
        local = kickoff.astimezone(SAO_PAULO)
        game["local_time"] = local
        if game["status"] != "FINISHED" or any(
            game[key] is None for key in ("home_id", "away_id", "home_goals", "away_goals")
        ):
            continue
        names[game["home_id"]] = game["home_name"]
        names[game["away_id"]] = game["away_name"]
        key = (game["home_goals"], game["away_goals"])
        by_exact[(game["local_time"], *key)].append(game)
        by_date_score[(game["local_time"].date(), *key)].append(game)

    votes: dict[int, Counter] = defaultdict(Counter)
    evidence: dict[tuple[int, int], list[int]] = defaultdict(list)
    issues = []
    parsed_games = []
    for game in cbf_games:
        try:
            kickoff = _match_time(game["details"][0])
            cbf_home, cbf_away = game["home_team_id"], game["away_team_id"]
            score = game["home_score"], game["away_score"]
            if None in (*score, cbf_home, cbf_away):
                raise ValueError
        except (ValueError, TypeError, KeyError, IndexError):
            issues.append({"code": "invalid_cbf_card", "cbf_match_id": game.get("match_id")})
            continue
        parsed_games.append((game, kickoff))
        exact = by_exact[(kickoff, *score)]
        if len(exact) == 1:
            candidate = exact[0]
            for cbf_id, fd_id in (
                (cbf_home, candidate["home_id"]),
                (cbf_away, candidate["away_id"]),
            ):
                votes[cbf_id][fd_id] += 1
                evidence[(cbf_id, fd_id)].append(game["match_id"])

    candidates = {}
    for team in teams:
        cbf_id = team["team_id"]
        ranking = votes[cbf_id].most_common()
        if (
            ranking
            and ranking[0][1] >= 3
            and (len(ranking) == 1 or ranking[0][1] - ranking[1][1] >= 3)
        ):
            candidates[cbf_id] = ranking[0][0]
    target_counts = Counter(candidates.values())
    candidates = {
        cbf_id: fd_id for cbf_id, fd_id in candidates.items() if target_counts[fd_id] == 1
    }

    linked = Counter()
    linked_matches = []
    time_differences = []
    for game, kickoff in parsed_games:
        home = candidates.get(game["home_team_id"])
        away = candidates.get(game["away_team_id"])
        if home is None or away is None:
            issues.append({"code": "unmapped_match", "cbf_match_id": game["match_id"]})
            continue
        matches = [
            fd
            for fd in by_date_score[(kickoff.date(), game["home_score"], game["away_score"])]
            if fd["home_id"] == home and fd["away_id"] == away
        ]
        if len(matches) != 1:
            issues.append({"code": "unmatched_fixture", "cbf_match_id": game["match_id"]})
            continue
        fd = matches[0]
        linked[game["home_team_id"]] += 1
        linked[game["away_team_id"]] += 1
        linked_matches.append(
            {"cbf_match_id": game["match_id"], "football_data_match_id": fd["external_id"]}
        )
        if fd["local_time"] != kickoff:
            time_differences.append(
                {
                    "cbf_match_id": game["match_id"],
                    "football_data_match_id": fd["external_id"],
                    "cbf_time": kickoff.isoformat(timespec="minutes"),
                    "football_data_time": fd["local_time"].isoformat(timespec="minutes"),
                }
            )

    team_links = []
    for team in sorted(teams, key=lambda item: item["team_id"]):
        cbf_id = team["team_id"]
        ranking = votes[cbf_id].most_common()
        candidate = candidates.get(cbf_id)
        team_links.append(
            {
                "cbf_team_id": cbf_id,
                "cbf_name": team["name"],
                "football_data_team_id": candidate,
                "football_data_name": names.get(candidate),
                "linked_fixtures": linked[cbf_id],
                "votes": [
                    {
                        "football_data_team_id": fd_id,
                        "count": count,
                        "cbf_match_ids": sorted(evidence[(cbf_id, fd_id)]),
                    }
                    for fd_id, count in ranking
                ],
                "status": "candidate" if candidate is not None else "unresolved",
            }
        )
    return {
        "season": season,
        "candidate_min_votes": 3,
        "cbf_games": len(cbf_games),
        "football_data_finished": sum(game["status"] == "FINISHED" for game in fd_games),
        "linked_games": len(linked_matches),
        "linked_matches": linked_matches,
        "team_links": team_links,
        "time_differences": time_differences,
        "issue_counts": dict(sorted(Counter(item["code"] for item in issues).items())),
        "issues": issues,
        "warning": "Vínculos são candidatos baseados em jogos; nenhum ID foi fundido ou usado no modelo.",
    }


def audit_team_links(database: Path, season: int) -> dict:
    """Lê observações atuais de Série A/CBF e BSA, sem alterar cadastros."""
    if not 2000 <= season <= 2100 or not database.is_file():
        raise ValueError("Temporada ou banco inválido")
    with sqlite3.connect(f"file:{quote(str(database.resolve()))}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        teams = [
            dict(row)
            for row in connection.execute(
                "SELECT team_id, name FROM cbf_teams WHERE season=? AND competition='serie-a'",
                (season,),
            )
        ]
        pages = [
            dict(row)
            for row in connection.execute(
                "SELECT id, team_id, data_json FROM cbf_team_pages "
                "WHERE season=? AND competition='serie-a' AND tab='historico-de-partidas' "
                "ORDER BY id DESC",
                (season,),
            )
        ]
        fd_games = [
            dict(row)
            for row in connection.execute(
                """WITH ranked AS (
                    SELECT external_id, kickoff_at, status, home_id, away_id,
                           home_name, away_name, home_goals, away_goals,
                           ROW_NUMBER() OVER (
                               PARTITION BY provider, external_id ORDER BY snapshot_id DESC
                           ) AS rank
                    FROM matches WHERE provider='football-data.org'
                                 AND competition_code='BSA' AND season_year=?
                ) SELECT external_id, kickoff_at, status, home_id, away_id,
                         home_name, away_name, home_goals, away_goals
                  FROM ranked WHERE rank=1""",
                (season,),
            )
        ]
    if not teams or not fd_games:
        raise ValueError("Dados CBF Série A ou BSA ausentes para a temporada")
    latest = {}
    for page in pages:
        latest.setdefault(page["team_id"], page)
    games = {}
    for page in latest.values():
        for game in json.loads(page["data_json"])["matches"]:
            match_id = game["match_id"]
            previous = games.setdefault(match_id, game)
            fields = ("url", "home_team_id", "away_team_id", "home_score", "away_score", "details")
            if any(previous.get(key) != game.get(key) for key in fields):
                raise ValueError(f"Cartões CBF contraditórios para o jogo {match_id}")
    report = _report(teams, list(games.values()), fd_games, season)
    report["indexed_teams"] = len(teams)
    report["history_pages"] = len(latest)
    report["history_coverage_complete"] = set(latest) == {team["team_id"] for team in teams}
    return report
