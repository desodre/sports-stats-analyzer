"""Vínculos candidatos entre provedores com evidência de partidas."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from typer.testing import CliRunner

from sports_stats_analyzer.cbf_identity import _report
from sports_stats_analyzer.cli import app


def test_links_require_repeated_match_evidence_and_keep_time_difference():
    teams = [{"team_id": 1, "name": "Time A"}, {"team_id": 2, "name": "Time B"}]
    cbf_games = []
    fd_games = []
    for index in range(5):
        day = index + 1
        cbf_games.append(
            {
                "match_id": 100 + index,
                "details": [f"{day:02d}/05/2026 - 16:00"],
                "home_team_id": 1,
                "away_team_id": 2,
                "home_score": 1,
                "away_score": 0,
            }
        )
        local = datetime(
            2026, 5, day, 16 if index < 4 else 17, 0, tzinfo=ZoneInfo("America/Sao_Paulo")
        )
        fd_games.append(
            {
                "external_id": 200 + index,
                "kickoff_at": local.astimezone(UTC).isoformat(),
                "status": "FINISHED",
                "home_id": 10,
                "away_id": 20,
                "home_name": "A FC",
                "away_name": "B FC",
                "home_goals": 1,
                "away_goals": 0,
            }
        )
    report = _report(teams, cbf_games, fd_games, 2026)
    assert report["linked_games"] == 5
    assert [link["football_data_team_id"] for link in report["team_links"]] == [10, 20]
    assert [link["votes"][0]["count"] for link in report["team_links"]] == [4, 4]
    assert report["time_differences"][0]["cbf_match_id"] == 104
    assert report["issue_counts"] == {}
    assert CliRunner().invoke(app, ["cbf-team-links", "--help"]).exit_code == 0
