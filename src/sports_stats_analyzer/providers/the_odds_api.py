"""Cliente mínimo da The Odds API para eventos e odds pré-jogo da Série A."""

import re
from typing import Self

import httpx

SPORT = "soccer_brazil_campeonato"


class OddsAPIError(Exception):
    """Falha da fonte sem expor a chave nem a URL requisitada."""


class TheOddsAPIClient:
    BASE_URL = "https://api.the-odds-api.com"

    def __init__(self, key: str, transport: httpx.BaseTransport | None = None) -> None:
        if not key.strip():
            raise OddsAPIError("Configure THE_ODDS_API_KEY no arquivo .env.")
        self._http = httpx.Client(
            base_url=self.BASE_URL,
            params={"apiKey": key},
            timeout=20,
            transport=transport,
            follow_redirects=False,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self._http.close()

    def _get(self, path: str, params: dict | None = None) -> object:
        try:
            response = self._http.get(path, params=params)
        except httpx.RequestError:
            raise OddsAPIError("Falha de conexão com The Odds API.") from None
        if response.status_code in (401, 403):
            raise OddsAPIError("Chave rejeitada ou recurso indisponível no plano da The Odds API.")
        if response.status_code == 429:
            raise OddsAPIError(
                "Cota da The Odds API atingida; aguarde antes de consultar novamente."
            )
        if not response.is_success:
            raise OddsAPIError(f"The Odds API respondeu HTTP {response.status_code}.")
        try:
            return response.json()
        except ValueError:
            raise OddsAPIError("The Odds API retornou JSON inválido.") from None

    def events(self) -> list[dict]:
        result = self._get(f"/v4/sports/{SPORT}/events")
        if not isinstance(result, list) or any(not isinstance(item, dict) for item in result):
            raise OddsAPIError("Formato inesperado dos eventos da The Odds API.")
        return result

    def event_odds(self, event_id: str, region: str = "eu") -> dict:
        if not re.fullmatch(r"[0-9a-fA-F]{32}", event_id):
            raise ValueError("ID de evento da The Odds API inválido.")
        if region not in {"eu", "uk", "us", "us2", "au"}:
            raise ValueError("Região inválida: use eu, uk, us, us2 ou au.")
        result = self._get(
            f"/v4/sports/{SPORT}/events/{event_id}/odds",
            {"regions": region, "markets": "h2h", "oddsFormat": "decimal"},
        )
        if not isinstance(result, dict):
            raise OddsAPIError("Formato inesperado das odds da The Odds API.")
        return result
