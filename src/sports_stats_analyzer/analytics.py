"""Qualidade e indicadores descritivos, sem previsões ou odds."""

from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from sports_stats_analyzer.domain import utc
from sports_stats_analyzer.repository import connect, match_versions


def eligible(match: dict) -> bool:
    return match["status"] == "FINISHED" and all(
        match[key] is not None for key in ("home_id", "away_id", "home_goals", "away_goals")
    )


def scope(rows, competition=None, season=None):
    return [
        m
        for m in rows
        if (
            competition is None
            or competition.upper() in (str(m["competition_id"]), m["competition_code"])
        )
        and (season is None or m["season_year"] == season)
    ]


def quality(database: Path, competition: str | None = None, season: int | None = None) -> dict:
    rows = scope(match_versions(database), competition, season)
    groups = {}
    for match in rows:
        key = (match["provider"], match["competition_id"], match["season_year"])
        groups.setdefault(key, []).append(match)
    reports = []
    for (provider, competition_id, year), matches in sorted(groups.items()):
        reports.append(
            {
                "provider": provider,
                "competition_id": competition_id,
                "competition_code": matches[0]["competition_code"],
                "season": year,
                "matches": len(matches),
                "statuses": dict(Counter(m["status"] for m in matches)),
                "eligible_results": sum(eligible(m) for m in matches),
                "missing_fields": {
                    key: sum(m[key] is None for m in matches)
                    for key in (
                        "home_id",
                        "away_id",
                        "home_goals",
                        "away_goals",
                        "duration",
                        "provider_updated_at",
                    )
                },
                "finished_without_regulation_score": sum(
                    m["status"] == "FINISHED"
                    and (m["home_goals"] is None or m["away_goals"] is None)
                    for m in matches
                ),
                "teams": len(
                    {
                        m[key]
                        for m in matches
                        for key in ("home_id", "away_id")
                        if m[key] is not None
                    }
                ),
                "first_kickoff": min(m["kickoff_at"] for m in matches),
                "last_kickoff": max(m["kickoff_at"] for m in matches),
                "latest_observation": max(m["fetched_at"] for m in matches),
            }
        )
    with connect(database) as connection:
        issues = [dict(row) for row in connection.execute("SELECT * FROM normalization_issues")]
        pending = connection.execute("""SELECT count(*) FROM snapshots WHERE id NOT IN
            (SELECT snapshot_id FROM normalization_runs)""").fetchone()[0]
    return {
        "groups": reports,
        "pending_snapshots": pending,
        "normalization_issues_all_snapshots": issues,
        "warning": "Completude dos registros coletados não comprova cobertura total da competição.",
    }


def team_report(
    database: Path,
    team_id: int,
    before: datetime,
    competition: str | None = None,
    season: int | None = None,
    window: int = 5,
    retrospective: bool = False,
) -> dict:
    before = utc(before)
    if window < 1 or team_id < 1:
        raise ValueError("Equipe e janela precisam ser positivas")
    rows = scope(match_versions(database, None if retrospective else before), competition, season)
    # Três horas são uma aproximação conservadora para exploração retrospectiva;
    # não uma evidência da hora em que um resultado ficou público.
    matches = sorted(
        (
            m
            for m in rows
            if eligible(m)
            and team_id in (m["home_id"], m["away_id"])
            and datetime.fromisoformat(m["kickoff_at"]) + timedelta(hours=3) < before
        ),
        key=lambda m: (m["kickoff_at"], m["external_id"]),
    )
    recent = matches[-window:]

    def aggregate(items):
        wins = draws = losses = goals_for = goals_against = 0
        results = []
        for match in items:
            home = match["home_id"] == team_id
            gf, ga = (
                (match["home_goals"], match["away_goals"])
                if home
                else (match["away_goals"], match["home_goals"])
            )
            goals_for += gf
            goals_against += ga
            wins += gf > ga
            draws += gf == ga
            losses += gf < ga
            results.append("W" if gf > ga else "D" if gf == ga else "L")
        n = len(items)
        return {
            "matches": n,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "form_oldest_first": results,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "goals_for_per_match": goals_for / n if n else None,
            "goals_against_per_match": goals_against / n if n else None,
            "points_per_match": (wins * 3 + draws) / n if n else None,
        }

    return {
        "team_id": team_id,
        "before": before.isoformat(),
        "competition": competition,
        "season": season,
        "requested_window": window,
        "available_matches": len(matches),
        "mode": "retrospective" if retrospective else "observed",
        "sample_status": "insufficient" if len(recent) < window else "window_complete",
        "overall": aggregate(recent),
        "home": aggregate([m for m in recent if m["home_id"] == team_id]),
        "away": aggregate([m for m in recent if m["away_id"] == team_id]),
        "days_since_last_kickoff_in_scope": (
            (before - datetime.fromisoformat(matches[-1]["kickoff_at"])).total_seconds() / 86400
            if matches
            else None
        ),
        "evidence": [
            {
                key: m[key]
                for key in (
                    "external_id",
                    "snapshot_id",
                    "fetched_at",
                    "kickoff_at",
                )
            }
            for m in recent
        ],
        "warnings": [
            "Intervalo desde último jogo no recorte; não mede descanso físico nem jogos em outras competições.",
            "Janela completa não implica amostra suficiente para treinar um modelo.",
        ]
        + (
            [
                "Exploração retrospectiva usa revisões coletadas depois do corte; não é backtest auditável."
            ]
            if retrospective
            else []
        ),
    }
