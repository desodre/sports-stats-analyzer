"""Contratos da fonte e conversão explícita de horários e placares."""

from datetime import UTC, date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Identifier = Annotated[int, Field(strict=True, gt=0)]
Goals = Annotated[int, Field(strict=True, ge=0)]


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Informe horário com fuso, por exemplo 2026-09-17T12:00:00Z")
    return value.astimezone(UTC)


class Competition(BaseModel):
    id: Identifier
    name: str = Field(min_length=1)
    code: str | None = None


class Season(BaseModel):
    id: Identifier
    startDate: date
    endDate: date

    @model_validator(mode="after")
    def ordered(self):
        if self.endDate < self.startDate:
            raise ValueError("Temporada com datas invertidas")
        return self


class Team(BaseModel):
    id: Identifier | None = None
    name: str | None = None


class ScorePair(BaseModel):
    home: Goals | None = None
    away: Goals | None = None


class Score(BaseModel):
    duration: Literal["REGULAR", "EXTRA_TIME", "PENALTY_SHOOTOUT"] | None = None
    fullTime: ScorePair = Field(default_factory=ScorePair)
    regularTime: ScorePair = Field(default_factory=ScorePair)

    def regulation(self) -> ScorePair:
        # fullTime pode incluir prorrogação; nunca subtrair ou presumir 90 minutos.
        return self.fullTime if self.duration == "REGULAR" else self.regularTime


class Match(BaseModel):
    id: Identifier
    competition: Competition
    season: Season
    utcDate: datetime
    lastUpdated: datetime | None = None
    status: Literal[
        "SCHEDULED",
        "TIMED",
        "IN_PLAY",
        "PAUSED",
        "EXTRA_TIME",
        "PENALTY_SHOOTOUT",
        "FINISHED",
        "SUSPENDED",
        "POSTPONED",
        "CANCELLED",
        "AWARDED",
    ]
    homeTeam: Team
    awayTeam: Team
    score: Score = Field(default_factory=Score)

    @field_validator("utcDate", "lastUpdated")
    @classmethod
    def timestamps(cls, value):
        return utc(value) if value is not None else None

    @model_validator(mode="after")
    def different_teams(self):
        if self.homeTeam.id is not None and self.homeTeam.id == self.awayTeam.id:
            raise ValueError("Mandante e visitante precisam ser diferentes")
        return self
