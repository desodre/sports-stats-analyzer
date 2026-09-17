"""Experimento temporal: seleção na validação, parâmetros congelados no teste."""

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from importlib.metadata import version
from itertools import pairwise
from pathlib import Path
from uuid import uuid4

from sports_stats_analyzer.analytics import eligible, scope
from sports_stats_analyzer.domain import utc
from sports_stats_analyzer.metrics import paired_interval, summarize
from sports_stats_analyzer.models import (
    FEATURE_VERSION,
    MODEL_VERSION,
    InsufficientData,
    baseline,
    fit_poisson,
    outcomes,
)
from sports_stats_analyzer.repository import match_versions


@dataclass(frozen=True)
class ExperimentConfig:
    competition: str
    train_start: datetime
    validation_start: datetime
    test_start: datetime
    test_end: datetime
    retrospective: bool = False
    min_train: int = 100
    min_team_matches: int = 5
    min_evaluation: int = 50

    def __post_init__(self):
        dates = [
            utc(d)
            for d in (self.train_start, self.validation_start, self.test_start, self.test_end)
        ]
        if not all(a < b for a, b in pairwise(dates)):
            raise ValueError("Exija train-start < validation-start < test-start < test-end")
        if min(self.min_train, self.min_team_matches, self.min_evaluation) < 1:
            raise ValueError("Mínimos de amostra precisam ser positivos")

    def metadata(self):
        return {
            key: utc(value).isoformat() if isinstance(value, datetime) else value
            for key, value in asdict(self).items()
        }


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def prior_results(rows: list[dict], start: datetime, cutoff: datetime) -> list[dict]:
    return [
        m
        for m in rows
        if eligible(m)
        and start <= datetime.fromisoformat(m["kickoff_at"])
        and datetime.fromisoformat(m["kickoff_at"]) + timedelta(hours=3) < cutoff
    ]


def walk_forward(
    database: Path,
    rows: list[dict],
    config: ExperimentConfig,
    start: datetime,
    end: datetime,
    candidates: list[dict],
) -> dict:
    buckets = {}
    for match in rows:
        kickoff = datetime.fromisoformat(match["kickoff_at"])
        if start <= kickoff < end and eligible(match):
            cutoff = start + timedelta(days=((kickoff - start).days // 7) * 7)
            buckets.setdefault(cutoff, []).append(match)
    result = {
        candidate["name"]: {
            "candidate": candidate,
            "predictions": [],
            "abstentions": [],
            "folds": [],
            "baseline_all": [],
        }
        for candidate in candidates
    }
    for cutoff, targets in sorted(buckets.items()):
        known = (
            rows
            if config.retrospective
            else scope(match_versions(database, cutoff), config.competition)
        )
        known_by_id = {(m["provider"], m["external_id"]): m for m in known}
        training = prior_results(known, config.train_start, cutoff)
        reference = baseline(training) if len(training) >= config.min_train else None
        fits = {}
        for candidate in candidates:
            penalty = candidate["penalty"]
            if penalty not in fits and reference is not None:
                try:
                    fits[penalty] = fit_poisson(training, penalty)
                except InsufficientData as error:
                    fits[penalty] = str(error)
            model = fits.get(penalty)
            run = result[candidate["name"]]
            fold_id = f"{candidate['name']}:{cutoff.isoformat()}"
            evidence = [
                {key: m[key] for key in ("provider", "external_id", "snapshot_id", "fetched_at")}
                for m in training
            ]
            run["folds"].append(
                {
                    "id": fold_id,
                    "cutoff": cutoff.isoformat(),
                    "train_size": len(training),
                    "train_last_kickoff": max((m["kickoff_at"] for m in training), default=None),
                    "train_fingerprint": digest(training),
                    "training_revisions": evidence,
                    "model": asdict(model)
                    if model is not None and not isinstance(model, str)
                    else None,
                    "model_error": model if isinstance(model, str) else None,
                }
            )
            for match in targets:
                item = {
                    "match_id": match["external_id"],
                    "home_id": match["home_id"],
                    "away_id": match["away_id"],
                    "provider": match["provider"],
                    "snapshot_id": match["snapshot_id"],
                    "kickoff": match["kickoff_at"],
                    "cutoff": cutoff.isoformat(),
                    "fold_id": fold_id,
                    "actual": outcomes(match),
                }
                fixture = known_by_id.get((match["provider"], match["external_id"]))
                reason = None
                if reference is None:
                    reason = "insufficient_training"
                elif not fixture or any(
                    fixture[key] != match[key] for key in ("home_id", "away_id", "kickoff_at")
                ):
                    reason = "fixture_not_known_at_cutoff"
                if reason is None:
                    run["baseline_all"].append({**item, "probabilities": reference})
                    if isinstance(model, str) or model is None:
                        reason = "optimizer_failure"
                    else:
                        try:
                            prediction = model.predict(
                                match["home_id"],
                                match["away_id"],
                                config.min_team_matches,
                                candidate["rho"],
                            )
                        except InsufficientData as error:
                            reason = str(error)
                if reason is not None:
                    run["abstentions"].append({**item, "reason": reason})
                else:
                    run["predictions"].append(
                        {**item, "probabilities": prediction, "baseline": reference}
                    )
        # The held-out block is only available as training in a later fold.
    for run in result.values():
        predictions = run["predictions"]
        actual = [p["actual"] for p in predictions]
        total = len(predictions) + len(run["abstentions"])
        run["summary"] = {
            "targets": total,
            "predicted": len(predictions),
            "coverage": len(predictions) / total if total else 0,
            "abstention_reasons": dict(Counter(p["reason"] for p in run["abstentions"])),
            "model": summarize([p["probabilities"] for p in predictions], actual),
            "paired_baseline": summarize([p["baseline"] for p in predictions], actual),
            "baseline_all": summarize(
                [p["probabilities"] for p in run["baseline_all"]],
                [p["actual"] for p in run["baseline_all"]],
            ),
        }
    return result


def run_experiment(database: Path, config: ExperimentConfig) -> dict:
    rows = scope(match_versions(database), config.competition)
    rows = sorted(
        (
            m
            for m in rows
            if config.train_start <= datetime.fromisoformat(m["kickoff_at"]) < config.test_end
        ),
        key=lambda m: (m["kickoff_at"], m["external_id"]),
    )
    if len({(m["provider"], m["competition_id"]) for m in rows}) != 1:
        raise ValueError("Selecione uma única competição/provedor com dados normalizados")
    candidates = [
        {"name": f"ridge-{penalty}-rho-{rho}", "penalty": penalty, "rho": rho}
        for penalty in (1.0, 10.0)
        for rho in (0.0, -0.1, 0.1)
    ]
    validation = walk_forward(
        database, rows, config, config.validation_start, config.test_start, candidates
    )
    # Compare all candidates on the exact same validation fixtures to avoid selection bias.
    shared = set.intersection(
        *({p["match_id"] for p in run["predictions"]} for run in validation.values())
    )
    targets = next(iter(validation.values()))["summary"]["targets"]
    if len(shared) < config.min_evaluation or len(shared) / max(1, targets) < 0.8:
        raise InsufficientData(
            "Validação sem amostra/cobertura suficiente. Verifique histórico e modo retrospectivo."
        )
    selection = {}
    for name, run in validation.items():
        selected = [p for p in run["predictions"] if p["match_id"] in shared]
        selection[name] = summarize(
            [p["probabilities"] for p in selected], [p["actual"] for p in selected]
        )
    best = min(selection, key=lambda name: selection[name]["markets"]["1x2"]["log_loss"])
    best_poisson = min(
        (c["name"] for c in candidates if c["rho"] == 0),
        key=lambda name: selection[name]["markets"]["1x2"]["log_loss"],
    )
    # Test only the preselected candidate and pure Poisson reference; no reselection on test.
    tested = [c for c in candidates if c["name"] in {best, best_poisson}]
    test = walk_forward(database, rows, config, config.test_start, config.test_end, tested)
    chosen = test[best]
    if len(chosen["predictions"]) < config.min_evaluation:
        raise InsufficientData(
            "Teste final sem amostra suficiente; amplie o período sem ajustar pelo resultado"
        )
    interval = paired_interval(chosen["predictions"])
    midpoint = config.test_start + (config.test_end - config.test_start) / 2
    subperiods = {}
    for name, predicate in (
        ("first_half", lambda p: datetime.fromisoformat(p["kickoff"]) < midpoint),
        ("second_half", lambda p: datetime.fromisoformat(p["kickoff"]) >= midpoint),
    ):
        subperiods[name] = paired_interval([p for p in chosen["predictions"] if predicate(p)])
    model_metrics = chosen["summary"]["model"]["markets"]["1x2"]
    baseline_metrics = chosen["summary"]["paired_baseline"]["markets"]["1x2"]
    checks = {
        "at_least_100_test_predictions": len(chosen["predictions"]) >= 100,
        "coverage_at_least_80_percent": chosen["summary"]["coverage"] >= 0.8,
        "ci95_upper_below_zero": interval["ci95"] is not None and interval["ci95"][1] < 0,
        "calibration_not_worse_by_more_than_0_02": model_metrics["classwise_ece_5_bins"]
        <= baseline_metrics["classwise_ece_5_bins"] + 0.02,
        "both_half_period_deltas_negative": all(
            part["mean_delta"] is not None and part["mean_delta"] < 0
            for part in subperiods.values()
        ),
    }
    code_hash = hashlib.sha256()
    for source in sorted(Path(__file__).parent.rglob("*.py")):
        code_hash.update(source.relative_to(Path(__file__).parent).as_posix().encode())
        code_hash.update(source.read_bytes())
    return {
        "schema_version": 1,
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "code_sha256": code_hash.hexdigest(),
        "dataset_sha256": digest(rows),
        "dependencies": {
            package: version(package) for package in ("numpy", "scipy", "sports-stats-analyzer")
        },
        "config": config.metadata(),
        "dataset_matches": len(rows),
        "protocol": {
            "fold_days": 7,
            "completion_buffer_hours": 3,
            "training": "expanding",
            "selection_metric": "1x2_log_loss",
            "validation_shared_matches": len(shared),
            "candidate_grid": candidates,
            "test_selection_frozen": True,
        },
        "selected_candidate": best,
        "selected_pure_poisson": best_poisson,
        "selection_metrics": selection,
        "validation": validation,
        "test": test,
        "paired_test_interval": interval,
        "test_subperiods": subperiods,
        "evidence_checks": checks,
        "decision_market": "1x2",
        "decision": "candidate_for_prospective_validation"
        if all(checks.values())
        else "baseline_retained",
        "warnings": [
            "Experimento retrospectivo com revisões atuais; não prova disponibilidade histórica das informações."
            if config.retrospective
            else "Treino e agenda filtrados pelas revisões observadas em cada corte.",
            "Correção Dixon–Coles aplicada após ajuste Poisson; não é estimação conjunta nem usa decaimento temporal.",
            "Bootstrap semanal é aproximado e não cobre todas as dependências entre times e períodos.",
            "Sem odds: este resultado não demonstra rentabilidade. Nenhum modelo é promovido automaticamente.",
        ],
    }


def save_experiment(database: Path, config: ExperimentConfig) -> dict:
    report = run_experiment(database, config)
    report["generated_at"] = datetime.now(UTC).isoformat()
    report["run_id"] = uuid4().hex
    directory = database.parent / "experiments"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{report['run_id']}.json"
    with target.open("x") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    selected = report["selected_candidate"]
    return {
        "artifact": str(target),
        "run_id": report["run_id"],
        "selected_candidate": selected,
        "dataset_matches": report["dataset_matches"],
        "test": report["test"][selected]["summary"],
        "paired_test_interval": report["paired_test_interval"],
        "decision": report["decision"],
        "decision_market": report["decision_market"],
        "evidence_checks": report["evidence_checks"],
        "warnings": report["warnings"],
    }
