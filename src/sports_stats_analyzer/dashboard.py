"""Painel local; consultas não acionam coleta, previsão ou aposta automaticamente."""

import json
import sqlite3
from datetime import UTC, datetime

import streamlit as st
from pydantic import ValidationError

from sports_stats_analyzer.analytics import quality, team_report
from sports_stats_analyzer.config import Settings
from sports_stats_analyzer.context import match_context
from sports_stats_analyzer.markets import create_forecast, wallet
from sports_stats_analyzer.monitoring import monitor
from sports_stats_analyzer.operations import backup, health, read_table, update
from sports_stats_analyzer.repository import match_versions


def render():
    st.set_page_config(page_title="Sports Stats Analyzer", page_icon="⚽", layout="wide")
    st.title("Sports Stats Analyzer")
    st.caption("Futebol • probabilidades experimentais • acompanhamento virtual")
    try:
        database = Settings().sports_database_path
    except ValidationError:
        st.error("Configuração local inválida. Confira o arquivo de ambiente.")
        return
    page = st.sidebar.radio("Navegação", ["Partidas", "Previsões", "Carteira virtual", "Operação"])
    competition = st.sidebar.text_input("Competição", value="BSA").strip().upper()
    season = st.sidebar.number_input(
        "Temporada", min_value=1900, max_value=2100, value=datetime.now(UTC).year
    )
    status = health(database, competition, season)
    if status["freshness"] == "fresh":
        st.caption(f"Fonte: football-data.org · observada em {status['observed_at']} (UTC)")
    else:
        st.warning("Dados ausentes ou com mais de 24 horas. Confira a atualização em Operação.")
    if status["last_update"] and status["last_update"]["status"] in {"failed", "running"}:
        st.warning(
            "Última atualização falhou ou não foi concluída; os dados anteriores foram preservados."
        )
    if page == "Operação":
        st.subheader("Atualização e qualidade")
        if st.button("Atualizar partidas", key="update"):
            with st.spinner("Consultando a fonte e normalizando os dados…"):
                result = update(database, competition, season)
            if result["status"] == "failed":
                st.error(
                    "Atualização falhou. Verifique conectividade, token e acesso à competição."
                )
            else:
                st.success(
                    "Atualização concluída."
                    if result["status"] == "success"
                    else "Atualização com registros em quarentena."
                )
            st.json(result)
        if database.is_file() and st.button("Criar backup", key="backup"):
            st.success(f"Backup verificado: {backup(database)['target']}")
        st.json(status)
        if database.is_file():
            try:
                st.json(quality(database, competition, season))
                st.subheader("Acompanhamento do modelo")
                st.json(monitor(database, competition))
            except (ValueError, sqlite3.Error):
                st.info("Ainda não há dados normalizados suficientes para os relatórios.")
        return
    if not database.is_file():
        st.info("Comece atualizando as partidas em Operação.")
        return
    try:
        rows = [m for m in match_versions(database) if m["competition_code"] == competition]
    except (ValueError, sqlite3.Error):
        st.info("Dados ainda não normalizados. Atualize as partidas em Operação.")
        return
    by_id = {m["external_id"]: m for m in rows}
    if page == "Partidas":
        rows = [m for m in rows if m["season_year"] == season]
        upcoming = st.checkbox("Somente partidas futuras", value=True)
        if upcoming:
            rows = [m for m in rows if datetime.fromisoformat(m["kickoff_at"]) > datetime.now(UTC)]
        rows.sort(key=lambda m: m["kickoff_at"])
        st.subheader("Agenda")
        if not rows:
            st.info("Nenhuma partida disponível para estes filtros.")
            return
        st.dataframe(
            [
                {
                    "ID": m["external_id"],
                    "Início UTC": m["kickoff_at"],
                    "Mandante": m["home_name"],
                    "Visitante": m["away_name"],
                    "Status": m["status"],
                }
                for m in rows
            ],
            hide_index=True,
        )
        selected = st.selectbox(
            "Analisar partida",
            [m["external_id"] for m in rows],
            format_func=lambda identifier: (
                f"{by_id[identifier]['home_name']} × {by_id[identifier]['away_name']} · {identifier}"
            ),
        )
        match = by_id[selected]
        st.caption(
            f"Resultado observado: {match['home_goals'] if match['home_goals'] is not None else '—'} × {match['away_goals'] if match['away_goals'] is not None else '—'} · {match['status']}"
        )
        if st.button("Registrar previsão experimental", key="forecast"):
            try:
                prediction = create_forecast(database, selected)
                st.success(f"Previsão registrada: {prediction['id']}")
                st.json(prediction)
            except ValueError:
                st.warning(
                    "Abstenção: confira início, histórico, atualização da agenda e competição suportada."
                )
        for column, side in zip(st.columns(2), ("home", "away"), strict=True):
            with column:
                st.subheader(match[f"{side}_name"] or "Equipe indefinida")
                if match[f"{side}_id"] is not None:
                    report = team_report(
                        database, match[f"{side}_id"], datetime.now(UTC), competition=competition
                    )
                    st.caption(
                        "Forma recente observada agora; não representa previsão histórica desta partida."
                    )
                    st.json(report["overall"])
        with st.expander("Escalações e origem das informações"):
            st.json(match_context(database, selected, datetime.now(UTC)))
    elif page == "Previsões":
        forecasts = [json.loads(r["payload"]) for r in read_table(database, "paper_forecasts")]
        forecasts = [
            p
            for p in forecasts
            if p["match_id"] in by_id and by_id[p["match_id"]]["season_year"] == season
        ]
        st.subheader("Histórico de previsões")
        st.info(
            "Probabilidades são estimativas. Intervalo de incerteza individual não estimado; sem garantia de lucro."
        )
        if not forecasts:
            st.info("Nenhuma previsão registrada para estes filtros.")
            return
        forecasts.sort(key=lambda p: p["created_at"], reverse=True)
        st.dataframe(
            [
                {
                    "Previsão": p["id"],
                    "Partida": p["match_id"],
                    "Emitida em UTC": p["created_at"],
                    "Mandante %": round(p["probabilities"]["1x2"][0] * 100, 2),
                    "Empate %": round(p["probabilities"]["1x2"][1] * 100, 2),
                    "Visitante %": round(p["probabilities"]["1x2"][2] * 100, 2),
                }
                for p in forecasts
            ],
            hide_index=True,
        )
        identifier = st.selectbox("Ver origem da previsão", [p["id"] for p in forecasts])
        prediction = next(p for p in forecasts if p["id"] == identifier)
        with st.expander("Dados e modelo usados"):
            st.json(
                {k: v for k, v in prediction.items() if k not in {"model", "training_revisions"}}
            )
            st.caption(
                f"Revisões usadas no treino: {len(prediction.get('training_revisions', []))}"
            )
    else:
        st.subheader("Carteira virtual · todas as partidas")
        report = wallet(database)
        columns = st.columns(3)
        columns[0].metric("Saldo disponível", report["available_balance"])
        columns[1].metric("Unidades reservadas", report["reserved"])
        columns[2].metric(
            "ROI liquidado", "Sem amostra" if report["roi"] is None else f"{report['roi']:.1%}"
        )
        st.caption("Simulação: 100 unidades iniciais, uma por aposta, máximo de cinco reservadas.")
        if not report["bets"]:
            st.info(
                "Nenhuma aposta virtual registrada. Cotações e decisões podem ser registradas pela CLI."
            )
        else:
            st.dataframe(
                [
                    {
                        k: b[k]
                        for k in ("id", "match_id", "placed_at", "status", "pnl", "settled_at")
                    }
                    for b in report["bets"]
                ],
                hide_index=True,
            )
            with st.expander("Decisões registradas"):
                st.json([json.loads(b["assessment"]) for b in report["bets"]])
        st.json({k: v for k, v in report.items() if k != "bets"})


def main():
    try:
        render()
    except (ValueError, OSError, sqlite3.Error, ValidationError):
        st.error(
            "Não foi possível carregar esta operação. Confira os dados e a configuração local."
        )


if __name__ == "__main__":
    main()
