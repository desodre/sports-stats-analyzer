import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from streamlit.testing.v1 import AppTest

from sports_stats_analyzer import dashboard, operations
from sports_stats_analyzer.normalization import normalize
from sports_stats_analyzer.storage import save_snapshot


def fixture_database(db):
    kickoff = datetime.now(UTC) + timedelta(days=1)
    match = {
        "id": 1,
        "utcDate": kickoff.isoformat(),
        "status": "POSTPONED",
        "competition": {"id": 2013, "code": "BSA", "name": "Brasileirão"},
        "season": {
            "id": 1,
            "startDate": f"{kickoff.year}-01-01",
            "endDate": f"{kickoff.year}-12-31",
        },
        "homeTeam": {"id": 10, "name": "Time A"},
        "awayTeam": {"id": 20, "name": "Time B"},
        "score": {"duration": "REGULAR", "fullTime": {"home": None, "away": None}},
    }
    save_snapshot(db, "competitions/BSA/matches", {"season": kickoff.year}, {"matches": [match]})
    normalize(db)


def test_empty_dashboard_and_failed_update(tmp_path, monkeypatch):
    monkeypatch.setenv("SPORTS_DATABASE_PATH", str(tmp_path / "missing.db"))
    monkeypatch.setenv("FOOTBALL_DATA_API_TOKEN", "NEVER_SHOW_THIS")
    monkeypatch.setattr(
        operations, "update", lambda *a: {"status": "failed", "error_kind": "ProviderError"}
    )
    app = AppTest.from_file(Path(dashboard.__file__)).run()
    assert not app.exception
    assert app.warning
    app.sidebar.radio[0].set_value("Operação").run()
    app.button(key="update").click().run()
    assert app.error
    assert not app.exception
    assert "NEVER_SHOW_THIS" not in str(app)


def test_dashboard_navigation_nullable_scores_and_abstention(tmp_path, monkeypatch):
    db = tmp_path / "sports.db"
    fixture_database(db)
    monkeypatch.setenv("SPORTS_DATABASE_PATH", str(db))
    app = AppTest.from_file(Path(dashboard.__file__)).run()
    assert not app.exception
    assert app.dataframe
    assert "POSTPONED" in str(app.dataframe[0].value)
    app.button(key="forecast").click().run()
    assert app.warning
    assert not app.exception
    app.sidebar.radio[0].set_value("Previsões").run()
    assert not app.exception
    assert any("Nenhuma previsão" in item.value for item in app.info)
    app.sidebar.radio[0].set_value("Carteira virtual").run()
    assert not app.exception
    assert app.metric[2].value == "Sem amostra"
    app.sidebar.radio[0].set_value("Operação").run()
    assert not app.exception
    assert app.json
    assert "insufficient_sample" in json.dumps([item.value for item in app.json])
