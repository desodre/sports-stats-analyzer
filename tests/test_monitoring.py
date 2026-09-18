import json
import math
from datetime import UTC, datetime, timedelta

import pytest

from sports_stats_analyzer import monitoring


def test_monitor_uses_last_pre_game_forecast_and_reports_distribution_shift(monkeypatch, tmp_path):
    now = datetime.now(UTC)
    rows = []
    for index in range(60):
        recent = index < 30
        kickoff = now - timedelta(days=10 + index if recent else 100 + index)
        rows.append(
            {
                "external_id": index + 1,
                "competition_code": "BSA",
                "status": "FINISHED",
                "kickoff_at": kickoff.isoformat(),
                "home_id": 1,
                "away_id": 2,
                "home_goals": 5 if recent else 1,
                "away_goals": 1,
            }
        )
    kickoff = datetime.fromisoformat(rows[0]["kickoff_at"])
    forecasts = []
    for hours, p in ((-2, 0.5), (-1, 0.6), (1, 0.9)):
        payload = {
            "match_id": 1,
            "home_id": 1,
            "away_id": 2,
            "kickoff": kickoff.isoformat(),
            "created_at": (kickoff + timedelta(hours=hours)).isoformat(),
            "mode": "prospective_paper",
            "probabilities": {"1x2": [p, (1 - p) / 2, (1 - p) / 2], "btts": 0.6, "over_2_5": 0.6},
        }
        forecasts.append({"created_at": payload["created_at"], "payload": json.dumps(payload)})
    monkeypatch.setattr(monitoring, "match_versions", lambda *args: rows)
    monkeypatch.setattr(monitoring, "read_table", lambda *args: forecasts)
    result = monitoring.monitor(tmp_path / "unused.db")
    assert result["forecast_evaluation"]["matches"] == 1
    assert result["forecast_evaluation"]["markets"]["1x2"]["log_loss"] == pytest.approx(
        -math.log(0.6)
    )
    assert result["goal_distribution"]["status"] == "watch"
    assert result["calibration_status"] == "insufficient_sample"
