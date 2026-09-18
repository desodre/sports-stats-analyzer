"""Integração síncrona com football-data.org v4."""

import time
from contextlib import nullcontext
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Self

import httpx

from sports_stats_analyzer.providers.rate_limit import RateGate


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
        self._gate = RateGate(token, self._interval) if transport is None else None
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
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        unfold: bool = False,
        attempts: int = 1,
    ) -> dict[str, Any]:
        if not 1 <= attempts <= 3:
            raise ValueError("Tentativas devem estar entre 1 e 3")
        for attempt in range(attempts):
            try:
                return self._get_once(endpoint, params, unfold=unfold)
            except TransientProviderError:
                if attempt + 1 == attempts:
                    raise
                time.sleep(2**attempt)
        raise AssertionError("unreachable")

    def _get_once(self, endpoint, params, *, unfold):
        # Só caminhos relativos: impedir envio do token para outro host.
        if endpoint.startswith("/") or ":" in endpoint or ".." in endpoint:
            raise ValueError("Endpoint deve ser um caminho relativo da API.")
        if self._gate is None and self._last_request is not None:
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
            with self._gate if self._gate is not None else nullcontext() as gate:
                response = self._http.get(endpoint, params=params, headers=headers)
                delay = 0.0
                for header in ("Retry-After", "X-RequestCounter-Reset"):
                    if (
                        header == "X-RequestCounter-Reset"
                        and response.status_code != 429
                        and response.headers.get("X-RequestsAvailable") != "0"
                    ):
                        continue
                    try:
                        value = float(response.headers.get(header, "0"))
                        if 0 < value < float("inf"):
                            delay = max(delay, value)
                    except ValueError:
                        if header == "Retry-After":
                            try:
                                retry_at = parsedate_to_datetime(response.headers[header])
                                delay = max(delay, (retry_at - datetime.now(UTC)).total_seconds())
                            except (ValueError, TypeError, OverflowError):
                                pass
                if gate is not None:
                    gate.defer(delay)
                elif delay:
                    if delay > 60:
                        raise ProviderError("Cota aguardando liberação; tente mais tarde")
                    time.sleep(delay)
        except ValueError as error:
            raise ProviderError(str(error)) from None
        except httpx.RequestError:
            raise TransientProviderError(
                "Falha de conexão com football-data.org; tente novamente."
            ) from None
        if response.status_code == 429:
            raise TransientProviderError(
                "Limite da API atingido (429). Aguarde antes de repetir a coleta."
            )
        if response.status_code >= 500:
            raise TransientProviderError(
                f"Serviço temporariamente indisponível (HTTP {response.status_code})."
            )
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


class TransientProviderError(ProviderError):
    """Rede, limite ou falha temporária do serviço; pode ser repetida com limite."""
