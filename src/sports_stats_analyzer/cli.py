"""Comandos da fase 1: coletar e preservar dados da fonte inicial."""

import json
import re
import sqlite3
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

import typer
from pydantic import ValidationError

from sports_stats_analyzer import analytics
from sports_stats_analyzer.config import Settings
from sports_stats_analyzer.normalization import normalize as normalize_data
from sports_stats_analyzer.providers.football_data import FootballDataClient, ProviderError
from sports_stats_analyzer.storage import save_snapshot

app = typer.Typer(help="Coleta auditável de futebol. Não produz recomendações de apostas.")


class Resource(StrEnum):
    competitions = "competitions"
    matches = "matches"
    teams = "teams"
    standings = "standings"


@app.command()
def collect(
    resource: Resource,
    competition: Annotated[str | None, typer.Option(help="Código (BSA, PL) ou ID.")] = None,
    season: Annotated[int | None, typer.Option(min=1900, max=2100)] = None,
    unfold: bool = False,
) -> None:
    """Coleta um recurso e salva um snapshot local em SQLite."""
    if resource != Resource.competitions and not competition:
        raise typer.BadParameter("Informe --competition para matches, teams ou standings.")
    if resource == Resource.competitions and (competition is not None or season is not None):
        raise typer.BadParameter("A listagem de competições não recebe competição ou temporada.")
    if competition and not re.fullmatch(r"[A-Za-z0-9]+", competition):
        raise typer.BadParameter("Competição deve ser um código ou ID alfanumérico.")
    if unfold and resource != Resource.matches:
        raise typer.BadParameter("--unfold aplica-se apenas a matches.")
    endpoint = (
        "competitions"
        if resource == Resource.competitions
        else f"competitions/{competition.upper()}/{resource.value}"
    )
    params = {} if season is None else {"season": season}
    try:
        settings = Settings()
        with FootballDataClient(
            settings.football_data_api_token.get_secret_value(),
            settings.football_data_requests_per_minute,
        ) as client:
            payload = (
                client.get(endpoint, params, unfold=True)
                if unfold
                else client.get(endpoint, params)
            )
        metadata = {**params, "_unfold": True} if unfold else params
        snapshot_id = save_snapshot(settings.sports_database_path, endpoint, metadata, payload)
    except ValidationError:
        typer.echo("Configuração inválida. Confira os valores do arquivo .env.", err=True)
        raise typer.Exit(1) from None
    except (ProviderError, sqlite3.Error, OSError) as error:
        typer.echo(f"Falha na coleta: {error}", err=True)
        raise typer.Exit(1) from None
    typer.echo(f"Snapshot {snapshot_id} salvo em {settings.sports_database_path}.")


@app.command()
def version() -> None:
    """Mostra a versão instalada."""
    from importlib.metadata import version as package_version

    typer.echo(package_version("sports-stats-analyzer"))


def local_report(action, **kwargs):
    try:
        result = action(Settings().sports_database_path, **kwargs)
    except ValidationError:
        typer.echo("Configuração inválida. Confira o arquivo .env.", err=True)
        raise typer.Exit(1) from None
    except (ValueError, sqlite3.Error, OSError) as error:
        typer.echo(f"Falha: {error}", err=True)
        raise typer.Exit(1) from None
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command()
def normalize() -> None:
    """Normaliza snapshots pendentes e registra dados inválidos em quarentena."""
    local_report(normalize_data)


@app.command()
def quality(competition: str | None = None, season: int | None = None) -> None:
    """Relata cobertura observada, campos ausentes e rejeições."""
    local_report(analytics.quality, competition=competition, season=season)


@app.command()
def team_report(
    team_id: Annotated[int, typer.Argument(min=1)],
    before: Annotated[
        str, typer.Option(help="Corte ISO 8601 com fuso; exemplo 2026-09-17T12:00:00Z")
    ],
    competition: str | None = None,
    season: int | None = None,
    window: Annotated[int, typer.Option(min=1)] = 5,
    retrospective: bool = False,
) -> None:
    """Indicadores anteriores ao corte. Modo retrospectivo é apenas exploratório."""
    try:
        cutoff = datetime.fromisoformat(before)
    except ValueError:
        raise typer.BadParameter("--before deve ser ISO 8601 com fuso horário") from None
    local_report(
        analytics.team_report,
        team_id=team_id,
        before=cutoff,
        competition=competition,
        season=season,
        window=window,
        retrospective=retrospective,
    )


@app.command()
def evaluate(
    competition: Annotated[str, typer.Option(help="Uma competição, por código ou ID")],
    train_season: Annotated[int, typer.Option(min=1900, max=2097)],
    validation_season: Annotated[int, typer.Option(min=1901, max=2098)],
    test_season: Annotated[int, typer.Option(min=1902, max=2099)],
    retrospective: bool = False,
) -> None:
    """Compara baseline, Poisson e correção de placares baixos por ano civil UTC."""
    from sports_stats_analyzer.evaluation import ExperimentConfig, save_experiment

    try:
        config = ExperimentConfig(
            competition=competition,
            train_start=datetime(train_season, 1, 1, tzinfo=UTC),
            validation_start=datetime(validation_season, 1, 1, tzinfo=UTC),
            test_start=datetime(test_season, 1, 1, tzinfo=UTC),
            test_end=datetime(test_season + 1, 1, 1, tzinfo=UTC),
            retrospective=retrospective,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from None
    local_report(save_experiment, config=config)


class ContextResource(StrEnum):
    match = "match"
    team = "team"
    person = "person"


@app.command()
def collect_context(
    resource: ContextResource, resource_id: Annotated[int, typer.Argument(min=1)]
) -> None:
    """Coleta detalhe de partida, equipe ou pessoa e preserva a observação."""
    from sports_stats_analyzer.context import collect_detail

    local_report(collect_detail, resource=resource.value, resource_id=resource_id)


@app.command()
def context_report(
    match_id: Annotated[int, typer.Argument(min=1)], before: Annotated[str, typer.Option()]
) -> None:
    """Relata contexto observado até --before (ISO 8601 com fuso)."""
    from sports_stats_analyzer.context import match_context

    try:
        cutoff = datetime.fromisoformat(before)
    except ValueError:
        raise typer.BadParameter("--before deve ser ISO 8601 com fuso") from None
    local_report(match_context, match_id=match_id, before=cutoff)


@app.command()
def context_coverage(competition: str | None = None, season: int | None = None) -> None:
    """Audita campos nas respostas armazenadas, distinguindo listas expandidas."""
    from sports_stats_analyzer.context import coverage

    local_report(coverage, competition=competition, season=season)


@app.command()
def squad_report(
    team_id: Annotated[int, typer.Argument(min=1)], before: Annotated[str, typer.Option()]
) -> None:
    """Relata elenco observado até --before; não é escalação."""
    from sports_stats_analyzer.context import squad_context

    try:
        cutoff = datetime.fromisoformat(before)
    except ValueError:
        raise typer.BadParameter("--before deve ser ISO 8601 com fuso") from None
    local_report(squad_context, team_id=team_id, before=cutoff)


@app.command()
def player_report(
    player_id: Annotated[int, typer.Argument(min=1)], before: Annotated[str, typer.Option()]
) -> None:
    """Perfil observado até --before, sem inferir desempenho ou disponibilidade."""
    from sports_stats_analyzer.context import player_context

    try:
        cutoff = datetime.fromisoformat(before)
    except ValueError:
        raise typer.BadParameter("--before deve ser ISO 8601 com fuso") from None
    local_report(player_context, player_id=player_id, before=cutoff)
