"""Integração síncrona com football-data.org v4."""

import time
from typing import Any, Self

import httpx


class ProviderError(Exception):
    """Falha recuperável de coleta, sem expor credenciais ou corpo remoto."""


class FootballDataClient:
    BASE_URL = "https://api.football-data.org/v4/"

    def __init__(
        self,
        token: str,
        requests_per_minute: int = 10,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not token.strip():
            raise ProviderError("Configure FOOTBALL_DATA_API_TOKEN no arquivo .env.")
        if requests_per_minute < 1:
            raise ValueError("requests_per_minute deve ser positivo")
        self._interval = 60 / requests_per_minute
        self._last_request: float | None = None
        self._http = httpx.Client(
            base_url=self.BASE_URL,
            headers={"X-Auth-Token": token},
            timeout=30,
            transport=transport,
            follow_redirects=False,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self._http.close()

    def get(
        self, endpoint: str, params: dict[str, Any] | None = None, *, unfold: bool = False
    ) -> dict[str, Any]:
        # Só caminhos relativos: impedir envio do token para outro host.
        if endpoint.startswith("/") or ":" in endpoint or ".." in endpoint:
            raise ValueError("Endpoint deve ser um caminho relativo da API.")
        if self._last_request is not None:
            time.sleep(max(0, self._interval - (time.monotonic() - self._last_request)))
        self._last_request = time.monotonic()
        try:
            headers = (
                {
                    f"X-Unfold-{field}": "true"
                    for field in (
                        "Lineups",
                        "Subs",
                        "Goals",
                        "Bookings",
                    )
                }
                if unfold
                else {}
            )
            response = self._http.get(endpoint, params=params, headers=headers)
        except httpx.RequestError:
            raise ProviderError(
                "Falha de conexão com football-data.org; tente novamente."
            ) from None
        if response.status_code == 429:
            raise ProviderError("Limite da API atingido (429). Aguarde antes de repetir a coleta.")
        if response.status_code in (401, 403):
            raise ProviderError("Acesso negado: confira o token e a cobertura do seu plano.")
        if response.status_code == 404:
            raise ProviderError("Recurso não encontrado: confira competição, temporada ou ID.")
        if not response.is_success:
            raise ProviderError(f"A API respondeu HTTP {response.status_code}; coleta não salva.")
        try:
            payload = response.json()
        except ValueError:
            raise ProviderError("Resposta da API não é JSON válido.") from None
        if not isinstance(payload, dict):
            raise ProviderError("Formato inesperado: a resposta deve ser um objeto JSON.")
        return payload
