"""Configuração local; tokens nunca fazem parte dos dados persistidos."""

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    football_data_api_token: SecretStr = SecretStr("")
    the_odds_api_key: SecretStr = SecretStr("")
    football_data_requests_per_minute: int = Field(default=10, ge=1, le=60)
    sports_database_path: Path = Path("data/sports.db")
    sports_rate_limit_dir: Path = Path("data/.rate-limits")
    sports_cbf_ca_bundle: Path | None = None
