"""Auditoria local das páginas de clubes CBF, sem conciliar identidades automaticamente."""

import hashlib
import json
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

from sports_stats_analyzer.providers.cbf_teams import TABS


def _name_key(name: str) -> str:
    plain = "".join(
        character
        for character in unicodedata.normalize("NFKD", name.casefold())
        if not unicodedata.combining(character)
    )
    words = re.findall(r"[a-z0-9]+", plain)
    while words and words[-1] in {"fc", "ec", "sc", "saf"}:
        words.pop()
    return " ".join(words)


def audit_team_pages(database: Path, season: int) -> dict:
    """Confere cobertura, conteúdo e arquivos; candidatos de identidade exigem revisão humana."""
    if not 2000 <= season <= 2100:
        raise ValueError("Temporada CBF inválida")
    if not database.is_file():
        raise ValueError("Banco CBF inexistente")
    with sqlite3.connect(f"file:{quote(str(database.resolve()))}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if not {"cbf_teams", "cbf_team_pages"} <= tables:
            raise ValueError("Banco sem coleta de clubes CBF")
        teams = [
            dict(row)
            for row in connection.execute(
                "SELECT competition, team_id, name, state FROM cbf_teams "
                "WHERE season=? ORDER BY competition, team_id",
                (season,),
            )
        ]
        pages = [
            dict(row)
            for row in connection.execute(
                "SELECT id, competition, team_id, tab, sha256, path, data_json "
                "FROM cbf_team_pages WHERE season=? ORDER BY id DESC",
                (season,),
            )
        ]
    if not teams:
        raise ValueError("Nenhum clube CBF registrado para a temporada")

    issues: list[dict] = []

    def issue(
        code: str,
        *,
        competition: str,
        team_id: int | None = None,
        tab: str | None = None,
        page_id: int | None = None,
    ) -> None:
        issues.append(
            {
                "code": code,
                "competition": competition,
                "team_id": team_id,
                "tab": tab,
                "page_id": page_id,
            }
        )

    root = (database.parent / "cbf").resolve()
    checked_files: dict[str, str | None] = {}
    latest = {}
    for page in pages:
        key = (page["competition"], page["team_id"], page["tab"])
        latest.setdefault(key, page)
        path = page["path"]
        if path not in checked_files:
            target = (root / path).resolve()
            if not target.is_relative_to(root) or not target.is_file():
                checked_files[path] = None
            else:
                checked_files[path] = hashlib.sha256(target.read_bytes()).hexdigest()
        actual = checked_files[path]
        if actual is None:
            issue(
                "missing_file",
                competition=page["competition"],
                team_id=page["team_id"],
                tab=page["tab"],
                page_id=page["id"],
            )
        elif actual != page["sha256"]:
            issue(
                "hash_mismatch",
                competition=page["competition"],
                team_id=page["team_id"],
                tab=page["tab"],
                page_id=page["id"],
            )

    memberships = {(team["competition"], team["team_id"]) for team in teams}
    for competition, team_id, tab in latest:
        if team_id is not None and (competition, team_id) not in memberships:
            issue(
                "orphan_page",
                competition=competition,
                team_id=team_id,
                tab=tab,
                page_id=latest[competition, team_id, tab]["id"],
            )

    grouped: dict[str, list[dict]] = defaultdict(list)
    candidates: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    by_id: dict[int, list[dict]] = defaultdict(list)
    for team in teams:
        grouped[team["competition"]].append(team)
        by_id[team["team_id"]].append(team)
        key = _name_key(team["name"])
        if key:
            candidates[(team["competition"], team["state"] or "", key)].append(
                {"team_id": team["team_id"], "name": team["name"], "state": team["state"]}
            )
    identity_candidates = [
        {"competition": competition, "state": state or None, "name_key": name, "members": members}
        for (competition, state, name), members in sorted(candidates.items())
        if len({member["team_id"] for member in members}) > 1
    ]
    id_conflicts = [
        {"team_id": team_id, "members": members}
        for team_id, members in sorted(by_id.items())
        if len({(_name_key(team["name"]), team["state"]) for team in members}) > 1
    ]

    coverage = []
    record_counts = Counter()
    for competition, members in sorted(grouped.items()):
        index = latest.get((competition, None, "index"))
        if index is None:
            issue("missing_index", competition=competition, tab="index")
        else:
            try:
                listed = json.loads(index["data_json"])["teams"]
                indexed_ids = {team["team_id"] for team in listed}
                if indexed_ids != {team["team_id"] for team in members}:
                    issue(
                        "index_membership_mismatch",
                        competition=competition,
                        tab="index",
                        page_id=index["id"],
                    )
                current = {team["team_id"]: team for team in members}
                if any(
                    team["team_id"] in current
                    and (
                        team.get("name") != current[team["team_id"]]["name"]
                        or team.get("state") != current[team["team_id"]]["state"]
                    )
                    for team in listed
                ):
                    issue(
                        "index_identity_mismatch",
                        competition=competition,
                        tab="index",
                        page_id=index["id"],
                    )
            except (ValueError, TypeError, KeyError):
                issue("invalid_payload", competition=competition, tab="index", page_id=index["id"])
        tabs = {}
        for tab in TABS:
            observed = nonempty = 0
            for team in members:
                team_id = team["team_id"]
                page = latest.get((competition, team_id, tab))
                if page is None:
                    issue("missing_tab", competition=competition, team_id=team_id, tab=tab)
                    continue
                observed += 1
                try:
                    payload = json.loads(page["data_json"])
                    key = {
                        "atletas": "listed_athletes",
                        "historico-de-partidas": "matches",
                        "estatisticas": "statistics",
                    }[tab]
                    content = payload[key]
                    if not isinstance(content, list if tab != "estatisticas" else dict):
                        raise TypeError
                except (ValueError, TypeError, KeyError):
                    issue(
                        "invalid_payload",
                        competition=competition,
                        team_id=team_id,
                        tab=tab,
                        page_id=page["id"],
                    )
                    continue
                if content:
                    nonempty += 1
                else:
                    issue(
                        "empty_content",
                        competition=competition,
                        team_id=team_id,
                        tab=tab,
                        page_id=page["id"],
                    )
                if tab == "atletas" and any(
                    not isinstance(athlete, dict) or not athlete.get("name") for athlete in content
                ):
                    issue(
                        "athlete_without_name",
                        competition=competition,
                        team_id=team_id,
                        tab=tab,
                        page_id=page["id"],
                    )
                if tab == "atletas":
                    record_counts["athlete_rows"] += len(content)
                if tab == "historico-de-partidas":
                    record_counts["match_cards"] += len(content)
                    record_counts["match_cards_with_result"] += sum(
                        isinstance(match, dict)
                        and all(
                            match.get(key) is not None
                            for key in ("home_team_id", "away_team_id", "home_score", "away_score")
                        )
                        for match in content
                    )
                    if any(
                        not isinstance(match, dict)
                        or not isinstance(match.get("match_id"), int)
                        or not match.get("url")
                        for match in content
                    ):
                        issue(
                            "invalid_match_reference",
                            competition=competition,
                            team_id=team_id,
                            tab=tab,
                            page_id=page["id"],
                        )
                    ids = [match.get("match_id") for match in content if isinstance(match, dict)]
                    if len(ids) != len(set(ids)):
                        issue(
                            "duplicate_match_reference",
                            competition=competition,
                            team_id=team_id,
                            tab=tab,
                            page_id=page["id"],
                        )
                    if any(
                        isinstance(match, dict)
                        and match.get("home_team_id") is not None
                        and match.get("away_team_id") is not None
                        and team_id not in (match["home_team_id"], match["away_team_id"])
                        for match in content
                    ):
                        issue(
                            "history_team_mismatch",
                            competition=competition,
                            team_id=team_id,
                            tab=tab,
                            page_id=page["id"],
                        )
                if tab == "estatisticas":
                    keys = ("played", "wins", "draws", "losses")
                    if not all(isinstance(content.get(key), int) for key in keys):
                        issue(
                            "incomplete_results",
                            competition=competition,
                            team_id=team_id,
                            tab=tab,
                            page_id=page["id"],
                        )
                    elif content["played"] != sum(content[key] for key in keys[1:]):
                        issue(
                            "results_total_mismatch",
                            competition=competition,
                            team_id=team_id,
                            tab=tab,
                            page_id=page["id"],
                        )
            tabs[tab] = {"observed": observed, "nonempty": nonempty, "expected": len(members)}
        coverage.append(
            {
                "competition": competition,
                "teams": len(members),
                "index_observed": index is not None,
                "tabs": tabs,
            }
        )

    return {
        "season": season,
        "teams": len(teams),
        "stored_pages": len(pages),
        "files_checked": len(checked_files),
        "record_counts": dict(sorted(record_counts.items())),
        "coverage": coverage,
        "issue_counts": dict(sorted(Counter(item["code"] for item in issues).items())),
        "issues": issues,
        "identity_candidates": identity_candidates,
        "id_conflicts": id_conflicts,
        "warning": "Listas vazias e nomes parecidos exigem revisão; nenhum ID foi fundido.",
    }
