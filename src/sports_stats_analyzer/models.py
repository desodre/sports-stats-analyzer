"""Baseline empírico e regressão Poisson com regularização das forças dos times."""

from collections import Counter
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson

MODEL_VERSION = "poisson-ridge-v1"
FEATURE_VERSION = "team-attack-defence-home-v1"


class InsufficientData(ValueError):
    """Abstenção: não há suporte suficiente para produzir uma estimativa."""


def outcomes(match: dict) -> dict:
    home, away = match["home_goals"], match["away_goals"]
    return {
        "1x2": 0 if home > away else 1 if home == away else 2,
        "over_2_5": int(home + away > 2),
        "btts": int(home > 0 and away > 0),
    }


def baseline(matches: list[dict]) -> dict:
    if not matches:
        raise InsufficientData("Treino vazio")
    labels = [outcomes(m) for m in matches]
    counts = np.bincount([item["1x2"] for item in labels], minlength=3)
    return {
        "1x2": ((counts + 1) / (len(matches) + 3)).tolist(),
        **{
            key: (sum(item[key] for item in labels) + 1) / (len(matches) + 2)
            for key in ("over_2_5", "btts")
        },
    }


def score_probabilities(home_rate: float, away_rate: float, rho: float = 0.0) -> dict:
    """Matriz adaptativa; correção Dixon–Coles opcional sobre os quatro placares baixos."""
    if not all(np.isfinite([home_rate, away_rate, rho])) or not (
        0 < home_rate <= 10 and 0 < away_rate <= 10
    ):
        raise InsufficientData("Taxas fora do domínio suportado (0, 10]")
    tolerance = 1e-10
    limit = max(2, int(poisson.ppf(1 - tolerance / 4, max(home_rate, away_rate))))
    support = np.arange(limit + 1)
    matrix = np.outer(poisson.pmf(support, home_rate), poisson.pmf(support, away_rate))
    factors = np.array(
        [[1 - home_rate * away_rate * rho, 1 + home_rate * rho], [1 + away_rate * rho, 1 - rho]]
    )
    if np.any(factors <= 0):
        raise InsufficientData("Correção de placares baixos geraria probabilidades inválidas")
    matrix[:2, :2] *= factors
    mass = float(matrix.sum())
    omitted = max(0.0, 1 - mass)
    if omitted > tolerance or mass <= 0:
        raise InsufficientData("Massa truncada excede tolerância")
    matrix /= mass
    home, away = np.indices(matrix.shape)
    return {
        "1x2": [
            float(matrix[home > away].sum()),
            float(np.trace(matrix)),
            float(matrix[home < away].sum()),
        ],
        "over_2_5": float(matrix[home + away > 2].sum()),
        "btts": float(matrix[1:, 1:].sum()),
        "expected_goals": {"home": home_rate, "away": away_rate},
        "omitted_mass": omitted,
        "max_goals": limit,
        "rho": rho,
    }


@dataclass
class PoissonModel:
    teams: list[int]
    counts: dict[int, int]
    parameters: list[float]
    penalty: float
    train_size: int

    def predict(
        self, home_id: int, away_id: int, min_team_matches: int = 5, rho: float = 0
    ) -> dict:
        if home_id == away_id:
            raise InsufficientData("Times iguais")
        if min(self.counts.get(home_id, 0), self.counts.get(away_id, 0)) < min_team_matches:
            raise InsufficientData("Equipe nova ou com poucos jogos no treino")
        if home_id not in self.teams or away_id not in self.teams:
            raise InsufficientData("Equipe fora do domínio treinado")
        n = len(self.teams)
        h, a = self.teams.index(home_id), self.teams.index(away_id)
        p = self.parameters
        home_rate = float(np.exp(p[0] + p[1] + p[2 + h] + p[2 + n + a]))
        away_rate = float(np.exp(p[0] + p[2 + a] + p[2 + n + h]))
        return score_probabilities(home_rate, away_rate, rho)


def fit_poisson(matches: list[dict], penalty: float = 10) -> PoissonModel:
    if not matches or not np.isfinite(penalty) or penalty <= 0:
        raise ValueError("Treino não vazio e penalidade finita positiva são obrigatórios")
    teams = sorted({m[key] for m in matches for key in ("home_id", "away_id")})
    indices = {team: i for i, team in enumerate(teams)}
    n, size = len(teams), len(matches)
    design = np.zeros((2 * size, 2 + 2 * n))
    response = np.zeros(2 * size)
    for i, match in enumerate(matches):
        h, a = indices[match["home_id"]], indices[match["away_id"]]
        design[2 * i, [0, 1, 2 + h, 2 + n + a]] = 1
        design[2 * i + 1, [0, 2 + a, 2 + n + h]] = 1
        response[2 * i : 2 * i + 2] = match["home_goals"], match["away_goals"]
    if not np.isfinite(response).all() or (response < 0).any():
        raise ValueError("Placares inválidos no treino")

    def objective(parameters):
        log_rates = design @ parameters
        rates = np.exp(log_rates)
        loss = np.sum(rates - response * log_rates) + penalty * np.sum(parameters[2:] ** 2) / 2
        gradient = design.T @ (rates - response)
        gradient[2:] += penalty * parameters[2:]
        return float(loss), gradient

    initial = np.zeros(2 + 2 * n)
    initial[0] = np.log(max(float(response.mean()), 0.1))
    result = minimize(
        objective,
        initial,
        jac=True,
        method="L-BFGS-B",
        bounds=[(-3, 3), (-2, 2)] + [(-2, 2)] * (2 * n),
        options={"maxiter": 500, "ftol": 1e-10},
    )
    if not result.success or not np.isfinite(result.x).all():
        raise InsufficientData("Otimização não convergiu")
    counts = Counter(m[key] for m in matches for key in ("home_id", "away_id"))
    return PoissonModel(teams, dict(counts), result.x.tolist(), penalty, size)
