"""Coleta conservadora e retomável de súmulas públicas das competições CBF selecionadas."""

import fcntl
import hashlib
import html
import os
import re
import sqlite3
import ssl
import tempfile
import time
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import httpx

COMPETITION_PATH = r"(?:campeonato-brasileiro/serie-[abcd]|copa-do-brasil/masculino)"
PAGE_PATH = re.compile(rf"/futebol-brasileiro/jogos/{COMPETITION_PATH}/(20\d{{2}})/.+")
TEAM_PATH = re.compile(rf"/futebol-brasileiro/times/({COMPETITION_PATH})/(20\d{{2}})(?:/(\d+))?")
PDF_PATH = re.compile(r"/sumulas/(20\d{2})/(\d+se\.pdf)")
PDF_LINK = re.compile(r"https://conteudo\.cbf\.com\.br/sumulas/20\d{2}/\d+se\.pdf")
MAX_PDF_BYTES = 10 * 1024 * 1024


class CBFError(ValueError):
    """Entrada ou resposta da CBF inesperada; não tentar outro host."""


class CBFRequestGate:
    """Um pedido a cada 15,1 s, inclusive entre processos e após reinícios.

    O instante é gravado antes da requisição. Assim, falhas e interrupções também
    consomem a cota; 15,1 s garantem no máximo 20 pedidos em qualquer janela de 5 min.
    """

    def __init__(self, directory: Path):
        self.path = directory / "cbf-public.lock"

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.path.open("a+") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                stream.seek(0)
                recorded = stream.read().strip()
                previous = float(recorded) if recorded else 0.0
                now = time.time()
                if previous > now + 300:
                    raise CBFError("Relógio local recuou; confira a sincronização antes de coletar")
                time.sleep(max(0.0, previous + 15.1 - now))
                stream.seek(0)
                stream.truncate()
                stream.write(str(time.time()))
                stream.flush()
                os.fsync(stream.fileno())
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)


def validate_url(url: str) -> tuple[str, int]:
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError as error:
        raise CBFError("URL inválida") from error
    if parsed.scheme != "https" or parsed.username or parsed.password or port or parsed.fragment:
        raise CBFError("URL deve ser HTTPS da página de jogo ou súmula da CBF")
    if parsed.hostname == "www.cbf.com.br":
        match = PAGE_PATH.fullmatch(parsed.path)
        if match:
            if parsed.query not in ("", "view=documentos"):
                raise CBFError("Página de jogo com parâmetros não permitidos")
            return "page", int(match.group(1))
        match = TEAM_PATH.fullmatch(parsed.path)
        if match:
            if match.group(3):
                if parsed.query not in (
                    "",
                    "tab=atletas",
                    "tab=historico-de-partidas",
                    "tab=estatisticas",
                ):
                    raise CBFError("Aba de clube não permitida")
                return "team_detail", int(match.group(2))
            if parsed.query:
                raise CBFError("Índice de clubes não aceita parâmetros")
            return "team_index", int(match.group(2))
        raise CBFError("Página deve ser de jogo ou clube das competições permitidas")
    if parsed.hostname == "conteudo.cbf.com.br":
        match = PDF_PATH.fullmatch(parsed.path)
        if not match or parsed.query:
            raise CBFError("PDF deve ser uma súmula oficial no diretório /sumulas/ da CBF")
        return "pdf", int(match.group(1))
    raise CBFError("Host não permitido; somente www.cbf.com.br e conteudo.cbf.com.br")


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            for key, value in attrs:
                if key == "href" and value:
                    self.hrefs.append(value)


def sumula_links(page: str, season: int) -> list[str]:
    parser = _Links()
    parser.feed(page)
    candidates = parser.hrefs + PDF_LINK.findall(html.unescape(page))
    found: list[str] = []
    for url in candidates:
        try:
            kind, year = validate_url(url)
        except CBFError:
            continue
        if kind == "pdf" and year == season and url not in found:
            found.append(url)
    return found


def _database(connection: sqlite3.Connection) -> None:
    connection.execute("""CREATE TABLE IF NOT EXISTS cbf_sumulas (
        id INTEGER PRIMARY KEY,
        source_url TEXT,
        document_url TEXT NOT NULL,
        season INTEGER NOT NULL,
        sha256 TEXT NOT NULL,
        path TEXT NOT NULL,
        fetched_at TEXT NOT NULL,
        etag TEXT,
        last_modified TEXT,
        UNIQUE (document_url, sha256)
    )""")


class CBFCollector:
    def __init__(
        self,
        database_path: Path,
        rate_limit_dir: Path,
        client: httpx.Client | None = None,
        ca_bundle: Path | None = None,
    ):
        self.database_path = database_path
        self.root = database_path.parent / "cbf"
        self.gate = CBFRequestGate(rate_limit_dir)
        verify: bool | ssl.SSLContext = True
        if ca_bundle is not None:
            if not ca_bundle.is_file():
                raise CBFError(f"Pacote de certificados inexistente: {ca_bundle}")
            context = ssl.create_default_context()
            context.load_verify_locations(cafile=str(ca_bundle))
            verify = context
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(30.0),
            follow_redirects=False,
            verify=verify,
            headers={"User-Agent": "sports-stats-analyzer/0.1 (authorized CBF research)"},
        )
        self._owns_client = client is None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        if self._owns_client:
            self.client.close()

    def _request(self, url: str, max_bytes: int) -> tuple[bytes, httpx.Headers]:
        validate_url(url)
        self.gate.acquire()
        try:
            with self.client.stream("GET", url) as response:
                response.raise_for_status()
                if response.is_redirect:
                    raise CBFError("Redirecionamento inesperado; não seguir para outro host")
                try:
                    declared_size = int(response.headers.get("content-length", "0"))
                except ValueError as error:
                    raise CBFError("Content-Length inválido na resposta") from error
                if declared_size > max_bytes:
                    raise CBFError("Resposta maior que o limite de segurança")
                chunks: list[bytes] = []
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > max_bytes:
                        raise CBFError("Resposta maior que o limite de segurança")
                    chunks.append(chunk)
                return b"".join(chunks), response.headers
        except httpx.HTTPError as error:
            raise CBFError(f"Falha HTTP em {url}: {error}") from error

    def _already_stored(self, url: str, connection: sqlite3.Connection) -> bool:
        rows = connection.execute(
            "SELECT path FROM cbf_sumulas WHERE document_url = ?", (url,)
        ).fetchall()
        return any((self.root / row[0]).is_file() for row in rows)

    def collect(self, urls: list[str], max_documents: int = 10, refresh: bool = False) -> dict:
        if max_documents < 1:
            raise CBFError("max_documents deve ser positivo")
        # Validar todas as entradas antes de qualquer contato com o servidor.
        inputs = list(dict.fromkeys(urls))
        for url in inputs:
            if validate_url(url)[0] not in ("page", "pdf"):
                raise CBFError("cbf-collect aceita somente páginas de jogo ou PDFs")
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        result: dict = {"pages": 0, "downloaded": 0, "skipped": 0, "documents": []}
        with sqlite3.connect(self.database_path) as connection:
            _database(connection)
            for source in inputs:
                if result["downloaded"] >= max_documents:
                    break
                kind, season = validate_url(source)
                if kind == "page":
                    parsed = urlparse(source)
                    page_url = urlunparse(parsed._replace(query="view=documentos"))
                    payload, _ = self._request(page_url, 5 * 1024 * 1024)
                    result["pages"] += 1
                    candidates = sumula_links(payload.decode("utf-8", errors="replace"), season)
                    if not candidates:
                        raise CBFError(f"Nenhuma súmula encontrada na página {page_url}")
                else:
                    candidates = [source]
                for document_url in candidates:
                    if result["downloaded"] >= max_documents:
                        return result
                    if not refresh and self._already_stored(document_url, connection):
                        result["skipped"] += 1
                        continue
                    pdf, headers = self._request(document_url, MAX_PDF_BYTES)
                    if not pdf.startswith(b"%PDF-") or b"%%EOF" not in pdf[-1024:]:
                        raise CBFError(f"Conteúdo não é um PDF completo: {document_url}")
                    digest = hashlib.sha256(pdf).hexdigest()
                    relative = Path("sumulas") / str(season) / f"{digest}.pdf"
                    target = self.root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists():
                        temporary: Path | None = None
                        try:
                            with tempfile.NamedTemporaryFile(
                                mode="wb", dir=target.parent, prefix=".cbf-", delete=False
                            ) as stream:
                                temporary = Path(stream.name)
                                stream.write(pdf)
                                stream.flush()
                                os.fsync(stream.fileno())
                            temporary.replace(target)
                        finally:
                            if temporary is not None:
                                temporary.unlink(missing_ok=True)
                    connection.execute(
                        """INSERT OR IGNORE INTO cbf_sumulas
                        (source_url, document_url, season, sha256, path, fetched_at, etag, last_modified)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            source if kind == "page" else None,
                            document_url,
                            season,
                            digest,
                            relative.as_posix(),
                            datetime.now(UTC).isoformat(),
                            headers.get("etag"),
                            headers.get("last-modified"),
                        ),
                    )
                    connection.commit()
                    result["downloaded"] += 1
                    result["documents"].append(
                        {"url": document_url, "sha256": digest, "path": str(target)}
                    )
        return result
