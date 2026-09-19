"""Catálogo local de URLs de jogos CBF a partir dos históricos dos clubes."""

import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote, urlparse

from sports_stats_analyzer.providers.cbf import CBFError, validate_url
from sports_stats_analyzer.providers.cbf_teams import COMPETITIONS


def _valid_match_url(url: object, competition: str, season: int, match_id: object) -> bool:
    if not isinstance(url, str) or not isinstance(match_id, int) or isinstance(match_id, bool):
        return False
    try:
        kind, year = validate_url(url)
    except CBFError:
        return False
    parsed = urlparse(url)
    path = parsed.path
    prefix = f"/futebol-brasileiro/jogos/{COMPETITIONS[competition]}/{season}/"
    return (
        kind == "page"
        and year == season
        and not parsed.query
        and path.startswith(prefix)
        and path.endswith(f"/{match_id}")
    )


def catalog_match_urls(database: Path, season: int) -> dict:
    """Deduplica cartões, preserva proveniência e sinaliza referências discordantes."""
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
                "SELECT competition, team_id FROM cbf_teams WHERE season=?", (season,)
            )
        ]
        pages = [
            dict(row)
            for row in connection.execute(
                "SELECT id, competition, team_id, data_json FROM cbf_team_pages "
                "WHERE season=? AND tab='historico-de-partidas' ORDER BY id DESC",
                (season,),
            )
        ]
    if not teams:
        raise ValueError("Nenhum clube CBF registrado para a temporada")

    members: dict[str, set[int]] = defaultdict(set)
    for team in teams:
        members[team["competition"]].add(team["team_id"])
    latest = {}
    for page in pages:
        latest.setdefault((page["competition"], page["team_id"]), page)

    issues: list[dict] = []
    grouped: dict[tuple[str, int], list[dict]] = defaultdict(list)
    card_counts = Counter()
    page_counts = Counter()
    for (competition, team_id), page in latest.items():
        if competition not in members or team_id not in members[competition]:
            issues.append({"code": "orphan_history_page", "page_id": page["id"]})
            continue
        page_counts[competition] += 1
        try:
            matches = json.loads(page["data_json"])["matches"]
            if not isinstance(matches, list):
                raise TypeError
        except (ValueError, TypeError, KeyError):
            issues.append({"code": "invalid_history_payload", "page_id": page["id"]})
            continue
        for match in matches:
            if not isinstance(match, dict) or not _valid_match_url(
                match.get("url"), competition, season, match.get("match_id")
            ):
                issues.append({"code": "invalid_match_url", "page_id": page["id"]})
                continue
            if all(match.get(key) is not None for key in ("home_team_id", "away_team_id")) and (
                team_id not in (match["home_team_id"], match["away_team_id"])
            ):
                issues.append({"code": "history_team_mismatch", "page_id": page["id"]})
                continue
            grouped[(competition, match["match_id"])].append(
                {
                    "url": match["url"],
                    "team_id": team_id,
                    "page_id": page["id"],
                    "home_team_id": match.get("home_team_id"),
                    "away_team_id": match.get("away_team_id"),
                    "home_score": match.get("home_score"),
                    "away_score": match.get("away_score"),
                }
            )
            card_counts[competition] += 1

    urls = []
    match_counts = Counter()
    paired_counts = Counter()
    single_counts = Counter()
    for (competition, match_id), observations in sorted(grouped.items()):
        if len({item["team_id"] for item in observations}) != len(observations):
            issues.append(
                {"code": "duplicate_match_card", "competition": competition, "match_id": match_id}
            )
            continue
        fields = ("url", "home_team_id", "away_team_id", "home_score", "away_score")
        if any(len({item[field] for item in observations}) > 1 for field in fields):
            issues.append(
                {"code": "conflicting_match_card", "competition": competition, "match_id": match_id}
            )
            continue
        match_counts[competition] += 1
        if len(observations) == 2:
            paired_counts[competition] += 1
        elif len(observations) == 1:
            single_counts[competition] += 1
        else:
            issues.append(
                {"code": "extra_match_card", "competition": competition, "match_id": match_id}
            )
            continue
        urls.append(
            {
                "competition": competition,
                "match_id": match_id,
                "url": observations[0]["url"],
                "source_page_ids": sorted(item["page_id"] for item in observations),
            }
        )

    coverage = [
        {
            "competition": competition,
            "indexed_teams": len(team_ids),
            "history_pages": page_counts[competition],
            "cards": card_counts[competition],
            "unique_matches": match_counts[competition],
            "paired_matches": paired_counts[competition],
            "single_ref_matches": single_counts[competition],
        }
        for competition, team_ids in sorted(members.items())
    ]
    return {
        "season": season,
        "coverage": coverage,
        "issue_counts": dict(sorted(Counter(issue["code"] for issue in issues).items())),
        "issues": issues,
        "urls": urls,
        "warning": "Cobertura de páginas não comprova calendário completo; cartões são dados pós-jogo.",
    }
