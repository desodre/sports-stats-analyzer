"""Cotações locais e carteira virtual prospectiva; não envia apostas a casas."""

import csv
import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Literal
from uuid import uuid4

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator

from sports_stats_analyzer.analytics import eligible
from sports_stats_analyzer.domain import Identifier, utc
from sports_stats_analyzer.evaluation import digest, prior_results
from sports_stats_analyzer.models import (
    FEATURE_VERSION,
    MODEL_VERSION,
    InsufficientData,
    fit_poisson,
)
from sports_stats_analyzer.repository import connect, match_versions

INITIAL_BALANCE = Decimal("100.00")
UNIT = Decimal("1.00")
MAX_EXPOSURE = Decimal("5.00")
QUOTE_TTL = timedelta(minutes=15)
FORECAST_TTL = timedelta(hours=24)
POLICY = "paper-v1"


def now() -> datetime:
    return datetime.now(UTC)


class Quote(BaseModel):
    model_config = {"extra": "forbid"}
    match_id: Identifier
    market: Literal["1x2", "total_goals", "btts"]
    selection: str
    line: Decimal | None = None
    odds: Decimal = Field(gt=1, le=1000, allow_inf_nan=False)
    bookmaker: str = Field(min_length=1)
    observed_at: datetime
    source: str = Field(min_length=1)

    @field_validator("observed_at")
    @classmethod
    def timestamp(cls, value):
        return utc(value)

    @field_validator("bookmaker", "source", "selection")
    @classmethod
    def nonblank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Campo vazio")
        return value

    @model_validator(mode="after")
    def compatible(self):
        allowed = {
            "1x2": {"home", "draw", "away"},
            "total_goals": {"over", "under"},
            "btts": {"yes", "no"},
        }
        if self.selection not in allowed[self.market]:
            raise ValueError("Seleção incompatível com o mercado")
        if self.market == "total_goals" and self.line != Decimal("2.5"):
            raise ValueError("Somente a linha 2.5 é suportada")
        if self.market != "total_goals" and self.line is not None:
            raise ValueError("Mercado sem linha deve usar line vazio")
        return self


def migrate(connection):
    connection.execute("""CREATE TABLE IF NOT EXISTS market_quotes (
        id TEXT PRIMARY KEY, identity_key TEXT UNIQUE NOT NULL,
        received_at TEXT NOT NULL, payload TEXT NOT NULL)""")
    connection.execute("""CREATE TABLE IF NOT EXISTS paper_forecasts (
        id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)""")
    connection.execute("""CREATE TABLE IF NOT EXISTS paper_bets (
        id TEXT PRIMARY KEY, match_id INTEGER UNIQUE NOT NULL,
        quote_id TEXT NOT NULL REFERENCES market_quotes(id),
        forecast_id TEXT NOT NULL REFERENCES paper_forecasts(id), placed_at TEXT NOT NULL,
        assessment TEXT NOT NULL, status TEXT NOT NULL,
        settled_at TEXT, result_snapshot INTEGER REFERENCES snapshots(id),
        pnl TEXT, settlement_reason TEXT)""")
    connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)")
    connection.execute("INSERT OR IGNORE INTO schema_migrations VALUES (2)")


def current_match(database: Path, match_id: int, cutoff: datetime) -> dict:
    matches = [
        m
        for m in match_versions(database, cutoff)
        if m["provider"] == "football-data.org" and m["external_id"] == match_id
    ]
    if not matches:
        raise ValueError("Partida não observada; colete e normalize os dados primeiro")
    return matches[0]


def import_quotes(database: Path, quotes: list[Quote]) -> dict:
    received = now()
    known = {
        m["external_id"]: m
        for m in match_versions(database, received)
        if m["provider"] == "football-data.org"
    }
    ids, inserted = [], 0
    with connect(database) as connection:
        connection.execute("BEGIN IMMEDIATE")
        migrate(connection)
        for quote in quotes:
            match = known.get(quote.match_id)
            if match is None:
                raise ValueError(f"Partida {quote.match_id} não está normalizada")
            kickoff = datetime.fromisoformat(match["kickoff_at"])
            if match["status"] not in {"SCHEDULED", "TIMED"} or received >= kickoff:
                raise ValueError("Importação prospectiva exige partida ainda não iniciada")
            if not timedelta(0) <= received - quote.observed_at <= QUOTE_TTL:
                raise ValueError("Cotação futura ou vencida: máximo de 15 minutos")
            payload = quote.model_dump(mode="json")
            payload["odds"] = str(quote.odds.normalize())
            payload["line"] = str(quote.line.normalize()) if quote.line is not None else None
            identity = digest({k: v for k, v in payload.items() if k != "odds"})
            quote_id = digest(payload)
            existing = connection.execute(
                "SELECT id FROM market_quotes WHERE identity_key=?", (identity,)
            ).fetchone()
            if existing and existing["id"] != quote_id:
                raise ValueError(
                    "Odds conflitantes para a mesma observação; corrija origem/horário"
                )
            if not existing:
                connection.execute(
                    "INSERT INTO market_quotes VALUES (?, ?, ?, ?)",
                    (quote_id, identity, received.isoformat(), json.dumps(payload)),
                )
                inserted += 1
            ids.append(quote_id)
    return {"inserted": inserted, "duplicates": len(quotes) - inserted, "quote_ids": ids}


def import_csv(database: Path, path: Path) -> dict:
    required = set(Quote.model_fields)
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if (
            reader.fieldnames is None
            or set(reader.fieldnames) != required
            or len(reader.fieldnames) != len(required)
        ):
            raise ValueError(f"CSV deve conter exatamente: {', '.join(sorted(required))}")
        quotes = []
        for number, row in enumerate(reader, start=2):
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("Número de campos inválido")
                row["match_id"] = int(row["match_id"])
                row["line"] = row["line"] or None
                quotes.append(Quote.model_validate(row))
            except (ValueError, TypeError):
                raise ValueError(f"CSV inválido na linha {number}") from None
    if not quotes:
        raise ValueError("CSV sem cotações")
    return import_quotes(database, quotes)


def create_forecast(database: Path, match_id: int) -> dict:
    created = now()
    match = current_match(database, match_id, created)
    kickoff = datetime.fromisoformat(match["kickoff_at"])
    if match["competition_code"] != "BSA":
        raise InsufficientData("Modelo experimental validado somente para BSA")
    if match["status"] not in {"SCHEDULED", "TIMED"} or kickoff <= created:
        raise InsufficientData("Previsão prospectiva exige partida ainda não iniciada")
    if created - datetime.fromisoformat(match["fetched_at"]) > FORECAST_TTL:
        raise InsufficientData("Atualize a agenda: snapshot da partida tem mais de 24 horas")
    training = prior_results(
        [
            m
            for m in match_versions(database, created)
            if m["competition_id"] == match["competition_id"] and m["provider"] == match["provider"]
        ],
        datetime(2023, 1, 1, tzinfo=UTC),
        created,
    )
    if len(training) < 100:
        raise InsufficientData("Menos de 100 partidas no treino expansivo desde 2023")
    if created - max(datetime.fromisoformat(m["kickoff_at"]) for m in training) > timedelta(
        days=45
    ):
        raise InsufficientData(
            "Histórico recente insuficiente; atualize resultados antes de prever"
        )
    model = fit_poisson(training, penalty=10)
    probabilities = model.predict(match["home_id"], match["away_id"], min_team_matches=5)
    payload = {
        "id": uuid4().hex,
        "created_at": created.isoformat(),
        "match_id": match_id,
        "kickoff": match["kickoff_at"],
        "home_id": match["home_id"],
        "away_id": match["away_id"],
        "fixture_snapshot": match["snapshot_id"],
        "probabilities": probabilities,
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "train_sha256": digest(training),
        "model": asdict(model),
        "training_revisions": [
            {k: m[k] for k in ("external_id", "snapshot_id", "fetched_at")} for m in training
        ],
        "mode": "prospective_paper",
        "policy": POLICY,
        "train_start": "2023-01-01T00:00:00+00:00",
        "warning": "Modelo experimental com treino expansivo desde 2023; sem promoção ou garantia de lucro.",
    }
    with connect(database) as connection:
        migrate(connection)
        connection.execute(
            "INSERT INTO paper_forecasts VALUES (?, ?, ?)",
            (payload["id"], payload["created_at"], json.dumps(payload, allow_nan=False)),
        )
    return {
        k: payload[k] for k in ("id", "match_id", "created_at", "probabilities", "mode", "warning")
    }


def selection_probability(probabilities: dict, market: str, selection: str) -> float:
    if market == "1x2":
        return probabilities["1x2"][["home", "draw", "away"].index(selection)]
    p = probabilities["over_2_5" if market == "total_goals" else "btts"]
    return p if selection in {"over", "yes"} else 1 - p


def expected_value(probability: float, odds: Decimal) -> float:
    if (
        not np.isfinite(probability)
        or not 0 <= probability <= 1
        or not odds.is_finite()
        or odds <= 1
    ):
        raise ValueError("Probabilidade ou odd inválida")
    return float(Decimal(str(probability)) * odds - 1)


def fair_market(quotes: list[Quote]) -> dict | None:
    if not quotes:
        return None
    first = quotes[0]

    def group(q):
        return q.match_id, q.market, q.line, q.bookmaker, q.observed_at, q.source

    selections = {
        "1x2": {"home", "draw", "away"},
        "total_goals": {"over", "under"},
        "btts": {"yes", "no"},
    }
    if (
        any(group(q) != group(first) for q in quotes)
        or {q.selection for q in quotes} != selections[first.market]
        or len(quotes) != len(selections[first.market])
    ):
        return None
    implied = {q.selection: Decimal(1) / q.odds for q in quotes}
    total = sum(implied.values())
    return {
        "method": "proportional_normalization",
        "overround": float(total - 1),
        "probabilities": {key: float(value / total) for key, value in implied.items()},
    }


def assess(database: Path, quote_id: str, forecast_id: str) -> dict:
    decision = now()
    with connect(database) as connection:
        migrate(connection)
        qrow = connection.execute("SELECT * FROM market_quotes WHERE id=?", (quote_id,)).fetchone()
        frow = connection.execute(
            "SELECT * FROM paper_forecasts WHERE id=?", (forecast_id,)
        ).fetchone()
        if not qrow or not frow:
            raise ValueError("Cotação ou previsão não encontrada")
        all_quotes = connection.execute(
            "SELECT * FROM market_quotes WHERE received_at<=?", (decision.isoformat(),)
        ).fetchall()
    quote = Quote.model_validate_json(qrow["payload"])
    forecast = json.loads(frow["payload"])
    if quote.match_id != forecast["match_id"]:
        raise ValueError("Cotação e previsão pertencem a partidas diferentes")
    match = current_match(database, quote.match_id, decision)
    reasons = []
    if not timedelta(0) <= decision - quote.observed_at <= QUOTE_TTL:
        reasons.append("quote_expired_or_future")
    if datetime.fromisoformat(qrow["received_at"]) > decision:
        reasons.append("quote_not_received_at_decision")
    if (
        not timedelta(0)
        <= decision - datetime.fromisoformat(forecast["created_at"])
        <= FORECAST_TTL
    ):
        reasons.append("forecast_expired_or_future")
    if decision >= datetime.fromisoformat(match["kickoff_at"]) or match["status"] not in {
        "TIMED",
        "SCHEDULED",
    }:
        reasons.append("match_not_pre_game")
    if any(
        match[key] != forecast[target]
        for key, target in (
            ("kickoff_at", "kickoff"),
            ("home_id", "home_id"),
            ("away_id", "away_id"),
        )
    ):
        reasons.append("fixture_changed")
    if decision - datetime.fromisoformat(match["fetched_at"]) > FORECAST_TTL:
        reasons.append("stale_fixture")
    if quote.market != "1x2" or match["competition_code"] != "BSA":
        reasons.append("market_or_competition_not_validated")
    p = selection_probability(forecast["probabilities"], quote.market, quote.selection)
    ev = expected_value(p, quote.odds)
    stressed_p = max(0.0, p - 0.05)
    stressed_ev = expected_value(stressed_p, quote.odds)
    if ev < 0.02 or stressed_ev <= 0:
        reasons.append("insufficient_edge_under_stress")
    peers = [Quote.model_validate_json(row["payload"]) for row in all_quotes]
    peers = [
        q
        for q in peers
        if (q.match_id, q.market, q.line, q.bookmaker, q.observed_at, q.source)
        == (
            quote.match_id,
            quote.market,
            quote.line,
            quote.bookmaker,
            quote.observed_at,
            quote.source,
        )
    ]
    return {
        "quote_id": quote_id,
        "forecast_id": forecast_id,
        "match_id": quote.match_id,
        "decision_at": decision.isoformat(),
        "policy": POLICY,
        "probability": p,
        "implied_probability": float(1 / quote.odds),
        "ev_per_unit": ev,
        "stress_probability": stressed_p,
        "stress_ev_per_unit": stressed_ev,
        "uncertainty_interval": None,
        "fair_market": fair_market(peers),
        "decision": "abstain" if reasons else "eligible_virtual",
        "reasons": reasons,
        "warning": "Redução de 5 pontos percentuais é cenário de sensibilidade, não intervalo de confiança.",
    }


def place_bet(database: Path, quote_id: str, forecast_id: str) -> dict:
    assessment = assess(database, quote_id, forecast_id)
    if assessment["decision"] != "eligible_virtual":
        return assessment
    with connect(database) as connection:
        connection.execute("BEGIN IMMEDIATE")
        migrate(connection)
        bets = connection.execute("SELECT * FROM paper_bets").fetchall()
        if any(b["match_id"] == assessment["match_id"] for b in bets):
            raise ValueError("Já existe aposta virtual para essa partida; limite de uma por jogo")
        reserved = sum(UNIT for b in bets if b["status"] == "open")
        realized = INITIAL_BALANCE + sum(Decimal(b["pnl"]) for b in bets if b["pnl"] is not None)
        if reserved + UNIT > MAX_EXPOSURE or realized - reserved < UNIT:
            raise ValueError("Limite de exposição ou saldo virtual insuficiente")
        bet_id = uuid4().hex
        connection.execute(
            """INSERT INTO paper_bets
            (id, match_id, quote_id, forecast_id, placed_at, assessment, status)
            VALUES (?, ?, ?, ?, ?, ?, 'open')""",
            (
                bet_id,
                assessment["match_id"],
                quote_id,
                forecast_id,
                assessment["decision_at"],
                json.dumps(assessment),
            ),
        )
    return {"bet_id": bet_id, "stake": str(UNIT), "status": "open", "assessment": assessment}


def settle(database: Path) -> dict:
    settled_at = now()
    known = {
        m["external_id"]: m
        for m in match_versions(database, settled_at)
        if m["provider"] == "football-data.org"
    }
    results = []
    with connect(database) as connection:
        connection.execute("BEGIN IMMEDIATE")
        migrate(connection)
        for bet in connection.execute("SELECT * FROM paper_bets WHERE status='open'").fetchall():
            match = known.get(bet["match_id"])
            if match is None:
                continue
            quote = Quote.model_validate_json(
                connection.execute(
                    "SELECT payload FROM market_quotes WHERE id=?", (bet["quote_id"],)
                ).fetchone()[0]
            )
            forecast = json.loads(
                connection.execute(
                    "SELECT payload FROM paper_forecasts WHERE id=?", (bet["forecast_id"],)
                ).fetchone()[0]
            )
            void = match["status"] in {"POSTPONED", "CANCELLED", "AWARDED"} or any(
                match[key] != forecast[target]
                for key, target in (
                    ("kickoff_at", "kickoff"),
                    ("home_id", "home_id"),
                    ("away_id", "away_id"),
                )
            )
            if void:
                status, pnl, reason = "void", Decimal(0), "void_status_or_fixture_changed"
            elif (
                eligible(match)
                and datetime.fromisoformat(match["kickoff_at"]) + timedelta(hours=3) < settled_at
            ):
                home, away = match["home_goals"], match["away_goals"]
                outcome = "home" if home > away else "draw" if home == away else "away"
                won = quote.selection == outcome
                status = "won" if won else "lost"
                pnl = (UNIT * (quote.odds - 1) if won else -UNIT).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                reason = "regulation_result"
            else:
                continue
            connection.execute(
                "UPDATE paper_bets SET status=?, settled_at=?, result_snapshot=?, pnl=?, settlement_reason=? WHERE id=?",
                (status, settled_at.isoformat(), match["snapshot_id"], str(pnl), reason, bet["id"]),
            )
            results.append({"bet_id": bet["id"], "status": status, "pnl": str(pnl)})
    return {
        "settled": results,
        "rule": "Canceladas, adiadas, atribuídas ou com agenda alterada são anuladas nesta simulação.",
    }


def wallet(database: Path) -> dict:
    with connect(database) as connection:
        migrate(connection)
        bets = [
            dict(row)
            for row in connection.execute("SELECT * FROM paper_bets ORDER BY settled_at, id")
        ]
    closed = [b for b in bets if b["status"] in {"won", "lost"}]
    realized = INITIAL_BALANCE + sum(Decimal(b["pnl"]) for b in bets if b["pnl"] is not None)
    reserved = sum(UNIT for b in bets if b["status"] == "open")
    balance, peak, drawdown = INITIAL_BALANCE, INITIAL_BALANCE, Decimal(0)
    grouped = {}
    for bet in bets:
        if bet["pnl"] is not None:
            grouped[bet["settled_at"]] = grouped.get(bet["settled_at"], Decimal(0)) + Decimal(
                bet["pnl"]
            )
    for pnl in grouped.values():
        balance += pnl
        peak = max(peak, balance)
        drawdown = max(drawdown, peak - balance)
    returns = np.array([float(b["pnl"]) for b in closed])
    interval = None
    if len(returns) >= 20:
        # Uma aposta por partida; reamostragem não cobre toda dependência temporal.
        samples = np.random.default_rng(42).choice(returns, size=(2000, len(returns))).mean(axis=1)
        interval = np.quantile(samples, [0.025, 0.975]).tolist()
    return {
        "policy": POLICY,
        "initial_balance": str(INITIAL_BALANCE),
        "realized_balance": str(realized),
        "reserved": str(reserved),
        "available_balance": str(realized - reserved),
        "max_realized_drawdown": str(drawdown),
        "settled_nonvoid": len(closed),
        "open": sum(b["status"] == "open" for b in bets),
        "void": sum(b["status"] == "void" for b in bets),
        "roi": float(returns.mean()) if len(returns) else None,
        "roi_bootstrap_ci95": interval,
        "bets": bets,
        "warnings": [
            "Somente saldo virtual. ROI exclui apostas abertas e anuladas.",
            "IC exploratório só com 20 apostas liquidadas; bootstrap por partida não cobre dependência temporal.",
            "Liquidações não são reescritas automaticamente após correções posteriores da fonte.",
        ],
    }
