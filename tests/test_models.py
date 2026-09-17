from types import SimpleNamespace

import numpy as np
import pytest
from scipy.stats import poisson

from sports_stats_analyzer.metrics import losses, paired_interval, summarize
from sports_stats_analyzer.models import (
    InsufficientData,
    baseline,
    fit_poisson,
    score_probabilities,
)


def training():
    return [
        {"home_id": h, "away_id": a, "home_goals": 2, "away_goals": 1}
        for _ in range(5)
        for h in range(4)
        for a in range(4)
        if h != a
    ]


def test_distribution_symmetry_and_analytic_binary_markets():
    prediction = score_probabilities(1.5, 1.5)
    assert sum(prediction["1x2"]) == pytest.approx(1)
    assert prediction["1x2"][0] == pytest.approx(prediction["1x2"][2])
    assert prediction["over_2_5"] == pytest.approx(poisson.sf(2, 3), abs=1e-9)
    assert prediction["btts"] == pytest.approx((1 - np.exp(-1.5)) ** 2, abs=1e-9)
    assert prediction["omitted_mass"] < 1e-10


@pytest.mark.parametrize("rates", [(0.01, 0.02), (10, 10), (5, 0.1)])
def test_tail_mass_extremes(rates):
    prediction = score_probabilities(*rates)
    assert np.isfinite(prediction["1x2"]).all()
    assert sum(prediction["1x2"]) == pytest.approx(1)
    assert prediction["omitted_mass"] <= 1e-10


def test_low_score_correction():
    independent = score_probabilities(1.4, 1.1)
    corrected = score_probabilities(1.4, 1.1, rho=-0.1)
    assert corrected["1x2"][1] > independent["1x2"][1]
    assert corrected["over_2_5"] == pytest.approx(independent["over_2_5"])
    assert sum(corrected["1x2"]) == pytest.approx(1)
    assert score_probabilities(1.4, 1.1, rho=0) == independent
    with pytest.raises(InsufficientData):
        score_probabilities(10, 10, rho=0.1)


@pytest.mark.parametrize("rate", [-1, 0, float("nan"), float("inf"), 11])
def test_invalid_rates_abstain(rate):
    with pytest.raises(InsufficientData):
        score_probabilities(rate, 1)


def test_poisson_learns_home_effect_and_abstains_for_unknown():
    model = fit_poisson(training())
    p = model.predict(0, 1)
    assert p["expected_goals"]["home"] == pytest.approx(2, abs=0.001)
    assert p["expected_goals"]["away"] == pytest.approx(1, abs=0.001)
    assert model.predict(2, 3)["1x2"] == pytest.approx(p["1x2"])
    with pytest.raises(InsufficientData):
        model.predict(99, 1)
    with pytest.raises(InsufficientData):
        model.predict(0, 1, min_team_matches=1000)


def test_optimizer_failure_abstains(monkeypatch):
    monkeypatch.setattr(
        "sports_stats_analyzer.models.minimize", lambda *a, **k: SimpleNamespace(success=False)
    )
    with pytest.raises(InsufficientData):
        fit_poisson(training())


def test_baseline_smoothing():
    p = baseline(training())
    assert all(v > 0 for v in p["1x2"])
    assert sum(p["1x2"]) == pytest.approx(1)
    assert p["1x2"][0] == pytest.approx(61 / 63)


def test_metrics_conventions_and_probability_validation():
    probabilities = [{"1x2": [0.5, 0.25, 0.25], "over_2_5": 0.5, "btts": 0.5}]
    actual = [{"1x2": 0, "over_2_5": 1, "btts": 0}]
    result = summarize(probabilities, actual)["markets"]
    assert result["1x2"]["log_loss"] == pytest.approx(np.log(2))
    assert result["1x2"]["brier"] == pytest.approx(0.375)
    assert result["over_2_5"]["brier"] == pytest.approx(0.25)
    with pytest.raises(ValueError):
        losses([{"1x2": [1, 1, 1]}], actual)


def test_calibration_includes_probability_one():
    result = summarize(
        [{"1x2": [1, 0, 0], "over_2_5": 1, "btts": 0}], [{"1x2": 0, "over_2_5": 1, "btts": 0}]
    )
    assert result["markets"]["1x2"]["classwise_ece_5_bins"] == 0
    assert sum(row["count"] for row in result["markets"]["1x2"]["calibration"]) == 3


def test_paired_interval_is_reproducible():
    predictions = [
        {
            "cutoff": str(i // 2),
            "actual": {"1x2": 0},
            "probabilities": {"1x2": [0.7, 0.2, 0.1]},
            "baseline": {"1x2": [0.5, 0.25, 0.25]},
        }
        for i in range(10)
    ]
    interval = paired_interval(predictions)
    assert interval == paired_interval(predictions)
    assert interval["ci95"][1] < 0
    assert interval["blocks"] == 5
