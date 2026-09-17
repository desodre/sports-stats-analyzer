"""Normalização idempotente; registros inválidos são rastreados em quarentena."""

import json
from pathlib import Path

from pydantic import ValidationError

from sports_stats_analyzer.domain import Competition, Match, Season, Team
from sports_stats_analyzer.repository import connect, migrate


def insert(connection, table, provider, snapshot_id, external_id, **fields):
    values = {
        "provider": provider,
        "external_id": external_id,
        "snapshot_id": snapshot_id,
        **fields,
    }
    connection.execute(
        f"INSERT OR IGNORE INTO {table} ({','.join(values)}) "
        f"VALUES ({','.join('?' for _ in values)})",
        tuple(values.values()),
    )


def competition_record(connection, provider, snapshot_id, item):
    insert(
        connection, "competitions", provider, snapshot_id, item.id, name=item.name, code=item.code
    )


def season_record(connection, provider, snapshot_id, item, competition_id):
    insert(
        connection,
        "seasons",
        provider,
        snapshot_id,
        item.id,
        competition_id=competition_id,
        start_date=item.startDate.isoformat(),
        end_date=item.endDate.isoformat(),
    )


def team_record(connection, provider, snapshot_id, item):
    if item.id is not None:
        insert(connection, "teams", provider, snapshot_id, item.id, name=item.name)


def normalize(database: Path) -> dict:
    summary = {"processed_snapshots": 0, "accepted": 0, "rejected": 0, "skipped": 0}
    with connect(database) as connection:
        connection.execute("BEGIN")
        migrate(connection)
        rows = connection.execute("""SELECT * FROM snapshots WHERE id NOT IN
            (SELECT snapshot_id FROM normalization_runs) ORDER BY id""").fetchall()
        for snapshot in rows:
            accepted = rejected = skipped = 0
            sid, provider = snapshot["id"], snapshot["provider"]
            payload = json.loads(snapshot["payload_json"])
            resource = snapshot["endpoint"].rstrip("/").split("/")[-1]
            if provider != "football-data.org" or resource not in {
                "matches",
                "teams",
                "competitions",
            }:
                skipped = 1
            else:
                if not isinstance(payload, dict) or not isinstance(payload.get(resource), list):
                    raise ValueError(f"Snapshot {sid}: coleção {resource} ausente ou inválida.")
                for index, record in enumerate(payload[resource]):
                    connection.execute("SAVEPOINT record")
                    try:
                        if resource == "matches":
                            match = Match.model_validate(record)
                            competition_record(connection, provider, sid, match.competition)
                            season_record(
                                connection, provider, sid, match.season, match.competition.id
                            )
                            team_record(connection, provider, sid, match.homeTeam)
                            team_record(connection, provider, sid, match.awayTeam)
                            score = match.score.regulation()
                            insert(
                                connection,
                                "matches",
                                provider,
                                sid,
                                match.id,
                                competition_id=match.competition.id,
                                competition_code=match.competition.code,
                                season_id=match.season.id,
                                season_year=match.season.startDate.year,
                                kickoff_at=match.utcDate.isoformat(),
                                provider_updated_at=match.lastUpdated.isoformat()
                                if match.lastUpdated
                                else None,
                                status=match.status,
                                home_id=match.homeTeam.id,
                                away_id=match.awayTeam.id,
                                home_name=match.homeTeam.name,
                                away_name=match.awayTeam.name,
                                duration=match.score.duration,
                                home_goals=score.home,
                                away_goals=score.away,
                            )
                        elif resource == "competitions":
                            item = Competition.model_validate(record)
                            competition_record(connection, provider, sid, item)
                        else:
                            comp = Competition.model_validate(payload.get("competition"))
                            season = Season.model_validate(payload.get("season"))
                            team = Team.model_validate(record)
                            if team.id is None:
                                raise ValueError("Equipe sem identificador")
                            competition_record(connection, provider, sid, comp)
                            season_record(connection, provider, sid, season, comp.id)
                            team_record(connection, provider, sid, team)
                        accepted += 1
                    except (ValidationError, ValueError) as error:
                        connection.execute("ROLLBACK TO record")
                        reason = (
                            "; ".join(
                                f"{'.'.join(map(str, e['loc']))}: {e['type']}"
                                for e in error.errors()
                            )
                            if isinstance(error, ValidationError)
                            else str(error)
                        )
                        connection.execute(
                            "INSERT INTO normalization_issues VALUES (?, ?, ?)",
                            (sid, index, reason),
                        )
                        rejected += 1
                    finally:
                        connection.execute("RELEASE record")
            connection.execute(
                "INSERT INTO normalization_runs VALUES (?, ?, ?, ?)",
                (sid, accepted, rejected, skipped),
            )
            summary["processed_snapshots"] += 1
            summary["accepted"] += accepted
            summary["rejected"] += rejected
            summary["skipped"] += skipped
    return summary
