import copy
import json
from datetime import UTC, datetime, timedelta

import pytest
from typer.testing import CliRunner

from sports_stats_analyzer.cli import app
from sports_stats_analyzer.evaluation import (
    ExperimentConfig,
    prior_results,
    run_experiment,
    walk_forward,
)
from sports_stats_analyzer.models import InsufficientData


def fixtures():
    start = datetime(2023, 1, 1, tzinfo=UTC)
    return [
        {
            "provider": "test",
            "external_id": i + 1,
            "snapshot_id": 1,
            "competition_id": 1,
            "competition_code": "TEST",
            "season_year": 2023,
            "kickoff_at": (start + timedelta(days=i, hours=12)).isoformat(),
            "fetched_at": "2026-01-01T00:00:00+00:00",
            "status": "FINISHED",
            "home_id": i % 4,
            "away_id": (i + 1) % 4,
            "home_goals": i % 3,
            "away_goals": (i // 2) % 3,
        }
        for i in range(100)
    ]


def config(retrospective=True):
    start = datetime(2023, 1, 1, tzinfo=UTC)
    return ExperimentConfig(
        "TEST",
        start,
        start + timedelta(days=30),
        start + timedelta(days=65),
        start + timedelta(days=100),
        retrospective,
        min_train=10,
        min_team_matches=1,
        min_evaluation=10,
    )


def test_cutoff_excludes_same_match_simultaneous_and_completion_buffer():
    rows = fixtures()
    cutoff = datetime.fromisoformat(rows[10]["kickoff_at"])
    train = prior_results(rows, config().train_start, cutoff)
    assert len(train) == 10
    assert all(datetime.fromisoformat(m["kickoff_at"]) + timedelta(hours=3) < cutoff for m in train)
    assert len(prior_results(rows, config().train_start, cutoff + timedelta(hours=2))) == 10


def test_walk_forward_ignores_future_scores(tmp_path):
    rows = fixtures()
    changed = copy.deepcopy(rows)
    for match in changed[70:]:
        match["home_goals"] = 9
    c = config()
    candidates = [{"name": "poisson", "penalty": 10, "rho": 0}]
    first = walk_forward(
        tmp_path / "unused.db", rows, c, c.validation_start, c.test_start, candidates
    )
    second = walk_forward(
        tmp_path / "unused.db", changed, c, c.validation_start, c.test_start, candidates
    )
    assert first == second
    for fold in first["poisson"]["folds"]:
        assert fold["train_last_kickoff"] < fold["cutoff"]


def test_test_labels_do_not_select_hyperparameters(tmp_path, monkeypatch):
    rows = fixtures()
    monkeypatch.setattr("sports_stats_analyzer.evaluation.match_versions", lambda *args: rows)
    first = run_experiment(tmp_path / "unused.db", config())
    for match in rows[65:]:
        match["home_goals"] = 4
    second = run_experiment(tmp_path / "unused.db", config())
    assert first["selected_candidate"] == second["selected_candidate"]
    assert first["selection_metrics"] == second["selection_metrics"]
    assert first["dataset_sha256"] != second["dataset_sha256"]
    assert first["protocol"]["test_selection_frozen"]
    assert len(first["test"]) <= 2


def test_observation_mode_does_not_reuse_late_results(tmp_path, monkeypatch):
    rows = fixtures()
    monkeypatch.setattr(
        "sports_stats_analyzer.evaluation.match_versions",
        lambda database, observed_at=None: rows if observed_at is None else [],
    )
    with pytest.raises(InsufficientData, match="Validação"):
        run_experiment(tmp_path / "unused.db", config(retrospective=False))


def test_fixture_revision_must_be_known_at_cutoff(tmp_path, monkeypatch):
    rows = fixtures()
    monkeypatch.setattr("sports_stats_analyzer.evaluation.match_versions", lambda *args: rows[:30])
    c = config(False)
    runs = walk_forward(
        tmp_path / "unused.db",
        rows,
        c,
        c.validation_start,
        c.test_start,
        [{"name": "p", "penalty": 10, "rho": 0}],
    )
    assert runs["p"]["summary"]["coverage"] == 0
    assert set(runs["p"]["summary"]["abstention_reasons"]) == {"fixture_not_known_at_cutoff"}


def test_invalid_order_rejected_and_cli_registered():
    c = config()
    with pytest.raises(ValueError):
        ExperimentConfig("TEST", c.test_start, c.validation_start, c.train_start, c.test_end)
    runner = CliRunner()
    assert "evaluate" in runner.invoke(app, ["--help"]).output
    result = runner.invoke(
        app,
        [
            "evaluate",
            "--competition",
            "BSA",
            "--train-season",
            "2025",
            "--validation-season",
            "2024",
            "--test-season",
            "2023",
        ],
    )
    assert result.exit_code == 2


def test_artifact_persistence(tmp_path, monkeypatch):
    from sports_stats_analyzer.evaluation import save_experiment

    monkeypatch.setattr("sports_stats_analyzer.evaluation.match_versions", lambda *args: fixtures())
    summary = save_experiment(tmp_path / "sports.db", config())
    with open(summary["artifact"]) as stream:
        report = json.load(stream)
    assert report["run_id"] == summary["run_id"]
    assert report["model_version"]
    assert report["code_sha256"]
    for run in report["test"].values():
        assert run["folds"][0]["model"]["parameters"]
        assert run["predictions"][0]["fold_id"] in {f["id"] for f in run["folds"]}
