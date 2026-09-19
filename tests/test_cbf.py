"""Coletor CBF: sem rede, com cota, integridade e retomada verificadas."""

import sqlite3
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from sports_stats_analyzer.cli import app
from sports_stats_analyzer.providers.cbf import (
    CBFCollector,
    CBFError,
    CBFRequestGate,
    sumula_links,
    validate_url,
)

GAME = (
    "https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/"
    "serie-a/2025/63238/20016/60175/20008/20014/60646/fortaleza-ec-saf-x-mirassol/829635"
)
PDF = "https://conteudo.cbf.com.br/sumulas/2025/142209se.pdf"
PDF_BODY = b"%PDF-1.4\nfixture\n%%EOF\n"


@pytest.mark.parametrize(
    "url",
    [
        "http://conteudo.cbf.com.br/sumulas/2025/142209se.pdf",
        "https://evil.example/sumulas/2025/142209se.pdf",
        "https://conteudo.cbf.com.br/sumulas/2025/142209b.pdf",
        PDF + "?token=x",
        GAME + "?view=documentos&x=1",
        GAME.replace("/serie-a/", "/serie-e/"),
        "https://www.cbf.com.br:invalida/futebol-brasileiro/jogos/campeonato-brasileiro/serie-a/2025/x",
    ],
)
def test_rejects_unapproved_urls(url):
    with pytest.raises(CBFError):
        validate_url(url)


def test_extracts_only_matching_season_sumulas():
    page = (
        f'<a href="{PDF}">Súmula</a>'
        '<a href="https://conteudo.cbf.com.br/sumulas/2025/142209b.pdf">Boletim</a>'
        '<a href="https://conteudo.cbf.com.br/sumulas/2026/142269se.pdf">Outro ano</a>'
    )
    assert sumula_links(page, 2025) == [PDF]


def test_requires_existing_ca_bundle_and_keeps_commands_separate(tmp_path):
    with pytest.raises(CBFError, match="Pacote de certificados inexistente"):
        CBFCollector(
            tmp_path / "sports.db", tmp_path / "limits", ca_bundle=tmp_path / "missing.pem"
        )
    instance = collector(tmp_path, lambda _: pytest.fail("network"))
    with pytest.raises(CBFError, match="somente páginas de jogo ou PDFs"):
        instance.collect(
            ["https://www.cbf.com.br/futebol-brasileiro/times/campeonato-brasileiro/serie-a/2026"]
        )


def test_gate_persists_before_request_and_spaces_processes(tmp_path, monkeypatch):
    clock = [1_000.0]
    slept = []

    def sleep(seconds):
        slept.append(seconds)
        clock[0] += seconds

    monkeypatch.setattr("sports_stats_analyzer.providers.cbf.time.time", lambda: clock[0])
    monkeypatch.setattr("sports_stats_analyzer.providers.cbf.time.sleep", sleep)
    CBFRequestGate(tmp_path).acquire()
    CBFRequestGate(tmp_path).acquire()
    assert slept == pytest.approx([0.0, 15.1])
    assert float((tmp_path / "cbf-public.lock").read_text()) == pytest.approx(1_015.1)


def test_gate_never_exceeds_twenty_requests_in_five_minutes(tmp_path, monkeypatch):
    clock = [10_000.0]
    issued = []

    def sleep(seconds):
        clock[0] += seconds

    monkeypatch.setattr("sports_stats_analyzer.providers.cbf.time.time", lambda: clock[0])
    monkeypatch.setattr("sports_stats_analyzer.providers.cbf.time.sleep", sleep)
    gate = CBFRequestGate(tmp_path)
    for _ in range(21):
        gate.acquire()
        issued.append(clock[0])
    assert issued[19] - issued[0] < 300
    assert issued[20] - issued[0] >= 300


def collector(tmp_path: Path, handler) -> CBFCollector:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    instance = CBFCollector(tmp_path / "sports.db", tmp_path / "limits", client=client)
    instance.gate.acquire = lambda: None
    return instance


def test_collects_resumes_and_records_provenance(tmp_path):
    requested = []

    def handler(request):
        requested.append(str(request.url))
        if request.url.host == "www.cbf.com.br":
            return httpx.Response(200, text=f'<a href="{PDF}">Súmula</a>')
        return httpx.Response(
            200,
            content=PDF_BODY,
            headers={"content-type": "application/pdf", "etag": '"revision-1"'},
        )

    instance = collector(tmp_path, handler)
    first = instance.collect([GAME])
    assert first["pages"] == 1
    assert first["downloaded"] == 1
    assert len(requested) == 2
    assert requested[0].endswith("?view=documentos")
    assert Path(first["documents"][0]["path"]).read_bytes() == PDF_BODY
    second = instance.collect([PDF])
    assert second["skipped"] == 1
    assert len(requested) == 2
    with sqlite3.connect(tmp_path / "sports.db") as connection:
        row = connection.execute(
            "SELECT source_url, document_url, season, etag FROM cbf_sumulas"
        ).fetchone()
    assert row == (GAME, PDF, 2025, '"revision-1"')


def test_rejects_invalid_pdf_without_persisting(tmp_path):
    instance = collector(tmp_path, lambda _: httpx.Response(200, content=b"<html>error</html>"))
    with pytest.raises(CBFError, match="PDF completo"):
        instance.collect([PDF])
    with sqlite3.connect(tmp_path / "sports.db") as connection:
        assert connection.execute("SELECT count(*) FROM cbf_sumulas").fetchone()[0] == 0


def test_refresh_preserves_both_pdf_revisions(tmp_path):
    body = [PDF_BODY]
    instance = collector(tmp_path, lambda _: httpx.Response(200, content=body[0]))
    first = instance.collect([PDF])["documents"][0]
    body[0] = b"%PDF-1.7\nrevised fixture\n%%EOF\n"
    second = instance.collect([PDF], refresh=True)["documents"][0]
    assert first["sha256"] != second["sha256"]
    assert Path(first["path"]).read_bytes() == PDF_BODY
    assert Path(second["path"]).read_bytes() == body[0]
    with sqlite3.connect(tmp_path / "sports.db") as connection:
        assert connection.execute("SELECT count(*) FROM cbf_sumulas").fetchone()[0] == 2


def test_redirect_is_not_followed(tmp_path):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(302, headers={"location": "https://evil.example/x"})

    instance = collector(tmp_path, handler)
    with pytest.raises(CBFError):
        instance.collect([PDF])
    assert seen == [PDF]


def test_limit_stops_before_next_page(tmp_path):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, content=PDF_BODY)

    instance = collector(tmp_path, handler)
    assert instance.collect([PDF, GAME], max_documents=1)["downloaded"] == 1
    assert seen == [PDF]


def test_cli_requires_input():
    result = CliRunner().invoke(app, ["cbf-collect"])
    assert result.exit_code == 2 or result.exit_code == 1
    assert "--url" in result.output
