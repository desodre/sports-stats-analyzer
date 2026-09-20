"""Índice e abas de clubes CBF: extração, cota do lote e retomada."""

import json
import sqlite3

import httpx
import pytest
from typer.testing import CliRunner

from sports_stats_analyzer.cli import app
from sports_stats_analyzer.providers.cbf import CBFError, CBFTransientError, validate_url
from sports_stats_analyzer.providers.cbf_teams import (
    CBFTeamCollector,
    index_url,
    parse_detail,
    parse_index,
    team_coverage,
)

INDEX = index_url("serie-a", 2026)
TEAM = INDEX + "/20052"
GAME = (
    "https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/"
    "serie-a/2026/coritiba-x-athletico/832158"
)
INDEX_HTML = (
    '<html><a href="/futebol-brasileiro/times/campeonato-brasileiro/serie-a/2026/20052">'
    "<strong>Athletico Paranaense<!-- --> - PR</strong></a>"
    '<a href="/futebol-brasileiro/times/campeonato-brasileiro/serie-b/2026/40000">'
    "<strong>Outro - SP</strong></a></html>"
)
ATHLETES_HTML = (
    "<html><table><thead><tr><th>Nome</th><th>Apelido</th><th>Clube Atual</th><th></th></tr></thead>"
    "<tbody><tr><td>João Silva</td><td>João</td><td>Athletico Paranaense</td><td></td></tr>"
    "</tbody></table></html>"
)
HISTORY_HTML = (
    '<html><a href="/futebol-brasileiro/jogos/campeonato-brasileiro/'
    'serie-a/2026/coritiba-x-athletico/832158">Documentos do jogo</a></html>'
)
HISTORY_CARD_HTML = (
    '<html><li class="splide__slide styles_splideItem__x"><div>'
    '<a href="/futebol-brasileiro/times/campeonato-brasileiro/serie-a/2026/111">'
    '<strong title="Mandante">Man</strong></a><span class="styles_gol__x">2</span>'
    '<a href="/futebol-brasileiro/times/campeonato-brasileiro/serie-a/2026/20052">'
    '<strong title="Athletico Paranaense">Ath</strong></a><span class="styles_gol__x">1</span>'
    '<span class="styles_numberGame__x">Jogo <!-- -->268</span>'
    "<p>11/09/2026 - 21:00<br/>Curitiba - PR<br/>Couto Pereira</p>"
    '<a href="/futebol-brasileiro/jogos/campeonato-brasileiro/serie-a/2026/'
    'coritiba-x-athletico/832158">Documentos do jogo</a></div></li></html>'
)
STATS_HTML = (
    "<html><div><h5>Gols Feitos</h5><span>41</span></div>"
    "<div><h5>Jogos disputados</h5><span>27</span></div></html>"
)


def test_url_allowlist_and_index_parser():
    assert validate_url(INDEX) == ("team_index", 2026)
    assert validate_url(TEAM + "?tab=estatisticas") == ("team_detail", 2026)
    assert parse_index(INDEX_HTML, "serie-a", 2026) == [
        {
            "team_id": 20052,
            "name": "Athletico Paranaense",
            "state": "PR",
            "url": TEAM,
        }
    ]
    with pytest.raises(CBFError):
        validate_url(TEAM + "?tab=segredo")
    with pytest.raises(CBFError):
        parse_index("<html>sem clubes</html>", "serie-a", 2026)


def test_detail_parser():
    assert parse_detail(ATHLETES_HTML, "serie-a", 2026, "atletas") == {
        "listed_athletes": [
            {
                "name": "João Silva",
                "nickname": "João",
                "current_club": "Athletico Paranaense",
            }
        ]
    }
    assert parse_detail(HISTORY_HTML, "serie-a", 2026, "historico-de-partidas") == {
        "matches": [{"match_id": 832158, "url": GAME}]
    }
    assert parse_detail(HISTORY_CARD_HTML, "serie-a", 2026, "historico-de-partidas") == {
        "matches": [
            {
                "game_number": 268,
                "details": ["11/09/2026 - 21:00", "Curitiba - PR", "Couto Pereira"],
                "match_id": 832158,
                "url": GAME,
                "home_team_id": 111,
                "away_team_id": 20052,
                "home_team": "Mandante",
                "away_team": "Athletico Paranaense",
                "home_score": 2,
                "away_score": 1,
            }
        ]
    }
    assert parse_detail(STATS_HTML, "serie-a", 2026, "estatisticas") == {
        "statistics": {"goals_for": 41, "played": 27}
    }
    with pytest.raises(CBFError):
        parse_detail("<html></html>", "serie-a", 2026, "estatisticas")
    with pytest.raises(CBFError):
        parse_detail("<html></html>", "serie-a", 2026, "atletas")


def test_collect_resumes_without_redownloading_and_reports_coverage(tmp_path):
    requested = []

    def handler(request):
        requested.append(str(request.url))
        if str(request.url) == INDEX:
            body = INDEX_HTML
        elif request.url.params.get("tab") == "atletas":
            body = ATHLETES_HTML
        elif request.url.params.get("tab") == "historico-de-partidas":
            body = HISTORY_HTML
        else:
            body = STATS_HTML
        return httpx.Response(200, text=body)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    instance = CBFTeamCollector(tmp_path / "sports.db", tmp_path / "limits", client=client)
    instance.gate.acquire = lambda: None
    first = instance.collect_teams(["serie-a"], 2026, max_requests=2)
    assert first == {
        "season": 2026,
        "requests": 2,
        "indexes": 1,
        "team_pages": 1,
        "skipped": 0,
        "unavailable": 0,
    }
    assert team_coverage(tmp_path / "sports.db", 2026) == [
        {"competition": "serie-a", "teams": 1, "athletes": 1, "history": 0, "statistics": 0}
    ]
    second = instance.collect_teams(["serie-a"], 2026, max_requests=2)
    assert second["requests"] == 2
    assert second["team_pages"] == 2
    assert len(requested) == 4
    assert team_coverage(tmp_path / "sports.db", 2026) == [
        {"competition": "serie-a", "teams": 1, "athletes": 1, "history": 1, "statistics": 1}
    ]
    third = instance.collect_teams(["serie-a"], 2026)
    assert third["requests"] == 0
    with sqlite3.connect(tmp_path / "sports.db") as connection:
        row = connection.execute(
            "SELECT data_json, path FROM cbf_team_pages WHERE tab = 'estatisticas'"
        ).fetchone()
    assert json.loads(row[0]) == {"statistics": {"goals_for": 41, "played": 27}}
    assert (tmp_path / "cbf" / row[1]).is_file()


def test_rejects_invalid_competition_before_network(tmp_path):
    instance = CBFTeamCollector(
        tmp_path / "sports.db",
        tmp_path / "limits",
        client=httpx.Client(transport=httpx.MockTransport(lambda _: pytest.fail("network"))),
    )
    with pytest.raises(CBFError):
        instance.collect_teams(["serie-e"], 2026)


def test_discovers_all_requested_competitions_before_team_pages(tmp_path):
    requested = []

    def handler(request):
        requested.append(str(request.url))
        html = (
            INDEX_HTML.replace("serie-a", "serie-b")
            if "serie-b" in str(request.url)
            else INDEX_HTML
        )
        return httpx.Response(200, text=html)

    instance = CBFTeamCollector(
        tmp_path / "sports.db",
        tmp_path / "limits",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    instance.gate.acquire = lambda: None
    result = instance.collect_teams(["serie-a", "serie-b"], 2026, max_requests=2)
    assert result["indexes"] == 2
    assert requested == [INDEX, index_url("serie-b", 2026)]
    assert [row["competition"] for row in team_coverage(tmp_path / "sports.db", 2026)] == [
        "serie-a",
        "serie-b",
    ]


def test_cached_index_rehydrates_memberships_after_interruption(tmp_path):
    requested = []

    def handler(request):
        requested.append(str(request.url))
        return httpx.Response(200, text=ATHLETES_HTML)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    instance = CBFTeamCollector(tmp_path / "sports.db", tmp_path / "limits", client=client)
    instance.gate.acquire = lambda: None
    with sqlite3.connect(tmp_path / "sports.db") as connection:
        from sports_stats_analyzer.providers.cbf_teams import _schema

        _schema(connection)
        instance._store(
            connection,
            url=INDEX,
            competition="serie-a",
            season=2026,
            team_id=None,
            tab="index",
            body=INDEX_HTML.encode(),
            parsed={"teams": parse_index(INDEX_HTML, "serie-a", 2026)},
        )
    result = instance.collect_teams(["serie-a"], 2026, max_requests=1)
    assert result["requests"] == 1
    assert requested == [TEAM + "?tab=atletas"]
    assert team_coverage(tmp_path / "sports.db", 2026)[0]["teams"] == 1


def test_detail_404_is_recorded_and_collection_continues(tmp_path):
    from sports_stats_analyzer.cbf_audit import audit_team_pages

    requested = []
    missing = {"value": True}

    def handler(request):
        url = str(request.url)
        requested.append(url)
        if url == INDEX:
            return httpx.Response(200, text=INDEX_HTML)
        if request.url.params.get("tab") == "atletas" and missing["value"]:
            return httpx.Response(404)
        body = {
            "atletas": ATHLETES_HTML,
            "historico-de-partidas": HISTORY_HTML,
            "estatisticas": STATS_HTML,
        }[request.url.params["tab"]]
        return httpx.Response(200, text=body)

    database = tmp_path / "sports.db"
    instance = CBFTeamCollector(
        database,
        tmp_path / "limits",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    instance.gate.acquire = lambda: None
    events = []
    first = instance.collect_teams(["serie-a"], 2026, progress=events.append)
    assert first == {
        "season": 2026,
        "requests": 4,
        "indexes": 1,
        "team_pages": 2,
        "skipped": 0,
        "unavailable": 1,
    }
    assert events[1]["status"] == "unavailable_404"
    assert requested == [
        INDEX,
        *(TEAM + f"?tab={tab}" for tab in ("atletas", "historico-de-partidas", "estatisticas")),
    ]
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT url, status_code FROM cbf_team_unavailable"
        ).fetchall() == [(TEAM + "?tab=atletas", 404)]
    audit = audit_team_pages(database, 2026)
    assert audit["coverage"][0]["tabs"]["atletas"] == {
        "observed": 0,
        "nonempty": 0,
        "unavailable": 1,
        "expected": 1,
    }
    assert audit["issue_counts"] == {"unavailable_404": 1, "incomplete_results": 1}

    second = instance.collect_teams(["serie-a"], 2026)
    assert second["requests"] == 0
    assert second["unavailable"] == 1
    assert len(requested) == 4

    missing["value"] = False
    refreshed = instance.collect_teams(["serie-a"], 2026, retry_unavailable=True)
    assert refreshed["requests"] == 1
    assert refreshed["unavailable"] == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM cbf_team_unavailable").fetchone()[0] == 0
    assert audit_team_pages(database, 2026)["coverage"][0]["tabs"]["atletas"]["observed"] == 1


@pytest.mark.parametrize("failure", [httpx.ConnectTimeout, httpx.ConnectError])
def test_transport_timeout_retries_with_gate_and_counts_every_attempt(tmp_path, failure):
    requested = []
    acquired = []

    def handler(request):
        requested.append(str(request.url))
        if str(request.url) == INDEX:
            return httpx.Response(200, text=INDEX_HTML)
        if request.url.params.get("tab") == "atletas" and requested.count(str(request.url)) == 1:
            raise failure("TLS handshake timed out")
        return httpx.Response(
            200,
            text={
                "atletas": ATHLETES_HTML,
                "historico-de-partidas": HISTORY_HTML,
                "estatisticas": STATS_HTML,
            }[request.url.params["tab"]],
        )

    instance = CBFTeamCollector(
        tmp_path / "sports.db",
        tmp_path / "limits",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    instance.gate.acquire = lambda: acquired.append(1)
    events = []
    result = instance.collect_teams(["serie-a"], 2026, progress=events.append)
    assert result["requests"] == 5
    assert result["team_pages"] == 3
    assert len(acquired) == len(requested) == 5
    assert events[1]["status"] == "retrying_transport"
    assert events[1]["attempt"] == 1
    assert events[2]["tab"] == "atletas"
    assert events[2]["requests"] == 3


def test_transport_retry_respects_request_limit_and_resumes(tmp_path):
    requested = []

    def handler(request):
        requested.append(str(request.url))
        if str(request.url) == INDEX:
            return httpx.Response(200, text=INDEX_HTML)
        if request.url.params.get("tab") == "atletas" and requested.count(str(request.url)) == 1:
            raise httpx.ConnectTimeout("TLS handshake timed out")
        return httpx.Response(200, text=ATHLETES_HTML)

    instance = CBFTeamCollector(
        tmp_path / "sports.db",
        tmp_path / "limits",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    instance.gate.acquire = lambda: None
    events = []
    first = instance.collect_teams(["serie-a"], 2026, max_requests=2, progress=events.append)
    assert first["requests"] == 2
    assert first["team_pages"] == 0
    assert events[-1]["status"] == "transport_deferred"
    second = instance.collect_teams(["serie-a"], 2026, max_requests=1)
    assert second["requests"] == 1
    assert second["team_pages"] == 1
    assert requested.count(TEAM + "?tab=atletas") == 2


def test_persistent_transport_timeout_fails_after_three_attempts(tmp_path):
    requested = []

    def handler(request):
        requested.append(str(request.url))
        if str(request.url) == INDEX:
            return httpx.Response(200, text=INDEX_HTML)
        raise httpx.ConnectTimeout("TLS handshake timed out")

    instance = CBFTeamCollector(
        tmp_path / "sports.db",
        tmp_path / "limits",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    instance.gate.acquire = lambda: None
    with pytest.raises(CBFTransientError, match="Falha temporária de rede"):
        instance.collect_teams(["serie-a"], 2026)
    assert requested == [INDEX] + [TEAM + "?tab=atletas"] * 3


@pytest.mark.parametrize("url", [INDEX, TEAM + "?tab=atletas"])
def test_index_404_and_detail_500_remain_fatal(tmp_path, url):
    def handler(request):
        if str(request.url) == url:
            return httpx.Response(404 if url == INDEX else 500)
        return httpx.Response(200, text=INDEX_HTML)

    instance = CBFTeamCollector(
        tmp_path / "sports.db",
        tmp_path / "limits",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    instance.gate.acquire = lambda: None
    with pytest.raises(CBFError):
        instance.collect_teams(["serie-a"], 2026)


def test_cli_exposes_team_commands():
    assert CliRunner().invoke(app, ["cbf-teams", "--help"]).exit_code == 0
    assert CliRunner().invoke(app, ["cbf-team-coverage", "--help"]).exit_code == 0
