"""Métricas observadas; não substituem novo teste reservado ou avaliação financeira."""

import json
from datetime import UTC, datetime, timedelta

from sports_stats_analyzer.analytics import eligible
from sports_stats_analyzer.metrics import summarize
from sports_stats_analyzer.models import outcomes
from sports_stats_analyzer.operations import read_table
from sports_stats_analyzer.repository import match_versions


def monitor(database, competition="BSA"):
    now = datetime.now(UTC)
    matches = [m for m in match_versions(database, now) if m["competition_code"] == competition]
    known = {m["external_id"]: m for m in matches}
    forecasts = {}
    for row in sorted(read_table(database, "paper_forecasts"), key=lambda r: r["created_at"]):
        payload = json.loads(row["payload"])
        match = known.get(payload["match_id"])
        if (
            match
            and eligible(match)
            and payload.get("mode") == "prospective_paper"
            and payload["created_at"] < match["kickoff_at"]
            and payload["kickoff"] == match["kickoff_at"]
            and payload["home_id"] == match["home_id"]
            and payload["away_id"] == match["away_id"]
            and datetime.fromisoformat(match["kickoff_at"]) + timedelta(hours=3) < now
        ):
            forecasts[payload["match_id"]] = payload
    predictions = list(forecasts.values())
    metrics = summarize(
        [p["probabilities"] for p in predictions],
        [outcomes(known[p["match_id"]]) for p in predictions],
    )
    periods = []
    for lower, upper in ((180, 90), (90, 0)):
        sample = [
            m
            for m in matches
            if eligible(m)
            and now - timedelta(days=lower)
            <= datetime.fromisoformat(m["kickoff_at"])
            < now - timedelta(days=upper)
            and datetime.fromisoformat(m["kickoff_at"]) + timedelta(hours=3) < now
        ]
        periods.append(
            {
                "matches": len(sample),
                "mean_total_goals": sum(m["home_goals"] + m["away_goals"] for m in sample)
                / len(sample)
                if sample
                else None,
            }
        )
    enough = min(p["matches"] for p in periods) >= 30
    delta = periods[1]["mean_total_goals"] - periods[0]["mean_total_goals"] if enough else None
    return {
        "forecast_evaluation": metrics,
        "calibration_status": "insufficient_sample" if len(predictions) < 20 else "exploratory",
        "goal_distribution": {
            "prior_90_days": periods[0],
            "recent_90_days": periods[1],
            "mean_difference": delta,
            "status": "insufficient_sample"
            if delta is None
            else "watch"
            if abs(delta) > 0.5
            else "stable_by_rule",
        },
        "warning": "Deslocamento de média é diagnóstico exploratório, não teste de drift; uma previsão por partida, última antes do início.",
    }
