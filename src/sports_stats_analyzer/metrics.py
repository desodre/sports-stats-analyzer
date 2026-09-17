"""Métricas probabilísticas e bootstrap pareado por bloco temporal."""

import numpy as np


def losses(probabilities: list[dict], actual: list[dict], market: str = "1x2"):
    if len(probabilities) != len(actual) or not actual:
        raise ValueError("Probabilidades e resultados devem ter mesmo tamanho não vazio")
    if market == "1x2":
        p = np.asarray([row[market] for row in probabilities], dtype=float)
        y = np.eye(3)[[row[market] for row in actual]]
    else:
        yes = np.asarray([row[market] for row in probabilities], dtype=float)
        p = np.column_stack((1 - yes, yes))
        y = np.eye(2)[[row[market] for row in actual]]
    if (
        not np.isfinite(p).all()
        or (p < 0).any()
        or (p > 1).any()
        or not np.allclose(p.sum(axis=1), 1, atol=1e-9)
    ):
        raise ValueError("Probabilidades inválidas")
    log_loss = -(y * np.log(np.clip(p, 1e-15, 1))).sum(axis=1)
    brier = ((p - y) ** 2).sum(axis=1)
    if market != "1x2":
        brier /= 2  # Binário usa (p - y)^2; 1X2 usa soma das três classes.
    return log_loss, brier, p, y


def summarize(probabilities: list[dict], actual: list[dict]) -> dict:
    if not actual:
        return {"matches": 0, "markets": {}}
    result = {"matches": len(actual), "markets": {}}
    for market in ("1x2", "over_2_5", "btts"):
        log_loss, brier, p, y = losses(probabilities, actual, market)
        bins = []
        for column in range(p.shape[1]):
            for lower in np.arange(0, 1, 0.2):
                upper = lower + 0.2
                selected = (p[:, column] >= lower) & (
                    p[:, column] <= 1 if upper > 0.999 else p[:, column] < upper
                )
                count = int(selected.sum())
                if count:
                    bins.append(
                        {
                            "class": column,
                            "lower": float(lower),
                            "upper": float(upper),
                            "count": count,
                            "mean_probability": float(p[selected, column].mean()),
                            "observed_frequency": float(y[selected, column].mean()),
                        }
                    )
        ece = sum(
            item["count"] * abs(item["mean_probability"] - item["observed_frequency"])
            for item in bins
        ) / (len(actual) * p.shape[1])
        result["markets"][market] = {
            "log_loss": float(log_loss.mean()),
            "brier": float(brier.mean()),
            "classwise_ece_5_bins": ece,
            "calibration": bins,
        }
    return result


def paired_interval(predictions: list[dict], seed: int = 42, repetitions: int = 2000) -> dict:
    if not predictions:
        return {"mean_delta": None, "ci95": None, "blocks": 0}
    actual = [row["actual"] for row in predictions]
    model_loss = losses([row["probabilities"] for row in predictions], actual)[0]
    reference_loss = losses([row["baseline"] for row in predictions], actual)[0]
    delta = model_loss - reference_loss
    blocks = sorted({row["cutoff"] for row in predictions})
    groups = [
        np.array([i for i, row in enumerate(predictions) if row["cutoff"] == block])
        for block in blocks
    ]
    if len(groups) < 2:
        return {"mean_delta": float(delta.mean()), "ci95": None, "blocks": len(groups)}
    totals = np.array([delta[group].sum() for group in groups])
    counts = np.array([len(group) for group in groups])
    chosen = np.random.default_rng(seed).integers(0, len(groups), size=(repetitions, len(groups)))
    boot = totals[chosen].sum(axis=1) / counts[chosen].sum(axis=1)
    return {
        "mean_delta": float(delta.mean()),
        "ci95": np.quantile(boot, [0.025, 0.975]).tolist(),
        "blocks": len(groups),
        "seed": seed,
        "repetitions": repetitions,
        "method": "paired-week-block-bootstrap",
        "negative_favors": "model",
    }
