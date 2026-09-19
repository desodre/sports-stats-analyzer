"""Observações de clubes CBF, por competição/temporada e aba pública."""

import hashlib
import json
import os
import re
import sqlite3
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

from sports_stats_analyzer.providers.cbf import (
    TEAM_PATH,
    CBFCollector,
    CBFError,
    CBFNotFound,
    validate_url,
)

BASE = "https://www.cbf.com.br"
COMPETITIONS = {
    "serie-a": "campeonato-brasileiro/serie-a",
    "serie-b": "campeonato-brasileiro/serie-b",
    "serie-c": "campeonato-brasileiro/serie-c",
    "serie-d": "campeonato-brasileiro/serie-d",
    "copa-do-brasil": "copa-do-brasil/masculino",
}
TABS = ("atletas", "historico-de-partidas", "estatisticas")
STATS = {
    "Gols Feitos": "goals_for",
    "Gols Sofridos": "goals_against",
    "Jogos sem sofrer gol": "clean_sheets",
    "Jogos disputados": "played",
    "Vitórias": "wins",
    "Derrotas": "losses",
    "Empates": "draws",
    "Cartões Amarelos": "yellow_cards",
    "Cartões Vermelhos": "red_cards",
}


def index_url(competition: str, season: int) -> str:
    if competition not in COMPETITIONS or not 2000 <= season <= 2100:
        raise CBFError("Competição ou temporada CBF não permitida")
    return f"{BASE}/futebol-brasileiro/times/{COMPETITIONS[competition]}/{season}"


class _IndexParser(HTMLParser):
    def __init__(self, competition: str, season: int):
        super().__init__()
        self.expected = f"/futebol-brasileiro/times/{COMPETITIONS[competition]}/{season}/"
        self.current: str | None = None
        self.in_strong = False
        self.parts: list[str] = []
        self.teams: dict[int, dict] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a":
            href = attributes.get("href") or ""
            if href.startswith(self.expected) and TEAM_PATH.fullmatch(href):
                self.current = href
                self.parts = []
        elif tag == "strong" and self.current:
            self.in_strong = True

    def handle_data(self, data: str) -> None:
        if self.current and self.in_strong:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "strong":
            self.in_strong = False
        elif tag == "a" and self.current:
            match = TEAM_PATH.fullmatch(self.current)
            title = "".join(self.parts).strip()
            if match and title:
                state_match = re.fullmatch(r"(.+?)\s+-\s+([A-Z]{2})", title)
                team_id = int(match.group(3))
                self.teams[team_id] = {
                    "team_id": team_id,
                    "name": state_match.group(1) if state_match else title,
                    "state": state_match.group(2) if state_match else None,
                    "url": urljoin(BASE, self.current),
                }
            self.current = None
            self.parts = []


def parse_index(page: str, competition: str, season: int) -> list[dict]:
    parser = _IndexParser(competition, season)
    parser.feed(page)
    teams = list(parser.teams.values())
    if not teams:
        raise CBFError(f"Índice sem clubes: {competition}/{season}")
    return teams


class _DetailParser(HTMLParser):
    def __init__(self, competition: str, season: int):
        super().__init__()
        self.competition = competition
        self.season = season
        self.rows: list[list[str]] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None
        self.header: str | None = None
        self.stat_label: str | None = None
        self.stats: dict[str, int] = {}
        self.matches: dict[int, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.row = []
        elif tag in ("th", "td") and self.row is not None:
            self.cell = []
        elif tag == "h5":
            self.header = ""
        elif tag == "span" and self.stat_label:
            self.cell = []
        elif tag == "a":
            href = dict(attrs).get("href") or ""
            if href.startswith("/futebol-brasileiro/jogos/"):
                url = urljoin(BASE, href)
                try:
                    kind, year = validate_url(url)
                except CBFError:
                    return
                parsed = urlparse(url)
                if (
                    kind == "page"
                    and year == self.season
                    and f"/{COMPETITIONS[self.competition]}/{self.season}/" in parsed.path
                ):
                    match_id = parsed.path.rsplit("/", 1)[-1]
                    if match_id.isdigit():
                        self.matches[int(match_id)] = url

    def handle_data(self, data: str) -> None:
        if self.header is not None:
            self.header += data
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h5" and self.header is not None:
            self.stat_label = self.header.strip() if self.header.strip() in STATS else None
            self.header = None
        elif tag == "span" and self.stat_label and self.cell is not None:
            value = "".join(self.cell).strip()
            if value.isdigit():
                self.stats[STATS[self.stat_label]] = int(value)
            self.stat_label = None
            self.cell = None
        elif tag in ("th", "td") and self.row is not None and self.cell is not None:
            self.row.append("".join(self.cell).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


class _HistoryParser(HTMLParser):
    """Lê cartões de jogos sem depender das classes CSS completas do build Next.js."""

    def __init__(self, competition: str, season: int):
        super().__init__()
        self.competition = competition
        self.season = season
        self.depth = 0
        self.card: dict | None = None
        self.capture: str | None = None
        self.capture_tag: str | None = None
        self.parts: list[str] = []
        self.matches: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if self.depth == 0:
            if tag != "li" or "splide__slide" not in (attributes.get("class") or ""):
                return
            self.card = {"team_ids": [], "team_names": [], "scores": []}
        self.depth += 1
        assert self.card is not None
        if tag == "a":
            href = attributes.get("href") or ""
            team = TEAM_PATH.fullmatch(href)
            if (
                team
                and team.group(1) == COMPETITIONS[self.competition]
                and int(team.group(2)) == self.season
                and team.group(3)
            ):
                self.card["team_ids"].append(int(team.group(3)))
            elif href.startswith("/futebol-brasileiro/jogos/"):
                url = urljoin(BASE, href)
                try:
                    kind, year = validate_url(url)
                except CBFError:
                    return
                if (
                    kind == "page"
                    and year == self.season
                    and f"/{COMPETITIONS[self.competition]}/{self.season}/" in href
                ):
                    match_id = href.rsplit("/", 1)[-1]
                    if match_id.isdigit():
                        self.card["match_id"] = int(match_id)
                        self.card["url"] = url
        elif tag == "strong" and attributes.get("title"):
            self.card["team_names"].append(attributes["title"])
        elif tag == "span" and "styles_gol" in (attributes.get("class") or ""):
            self.capture, self.capture_tag, self.parts = "score", "span", []
        elif tag == "span" and "styles_numberGame" in (attributes.get("class") or ""):
            self.capture, self.capture_tag, self.parts = "number", "span", []
        elif tag == "p" and self.capture is None:
            self.capture, self.capture_tag, self.parts = "details", "p", []
        elif tag == "br" and self.capture == "details":
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.depth and self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self.depth:
            return
        assert self.card is not None
        if tag == self.capture_tag:
            value = "".join(self.parts).strip()
            if self.capture == "score" and value.isdigit():
                self.card["scores"].append(int(value))
            elif self.capture == "number":
                match = re.search(r"\d+", value)
                if match:
                    self.card["game_number"] = int(match.group())
            elif self.capture == "details":
                lines = [" ".join(line.split()) for line in value.split("\n")]
                self.card["details"] = [line for line in lines if line]
            self.capture, self.capture_tag, self.parts = None, None, []
        self.depth -= 1
        if self.depth == 0:
            if "url" in self.card:
                teams = self.card.pop("team_ids")
                names = self.card.pop("team_names")
                scores = self.card.pop("scores")
                self.card["home_team_id"] = teams[0] if len(teams) > 0 else None
                self.card["away_team_id"] = teams[1] if len(teams) > 1 else None
                self.card["home_team"] = names[0] if len(names) > 0 else None
                self.card["away_team"] = names[1] if len(names) > 1 else None
                self.card["home_score"] = scores[0] if len(scores) > 0 else None
                self.card["away_score"] = scores[1] if len(scores) > 1 else None
                self.matches.append(self.card)
            self.card = None


def parse_detail(page: str, competition: str, season: int, tab: str) -> dict:
    if tab not in TABS:
        raise CBFError("Aba de clube não permitida")
    parser = _DetailParser(competition, season)
    parser.feed(page)
    if tab == "estatisticas":
        if not parser.stats:
            raise CBFError("Aba de estatísticas sem métricas reconhecidas")
        return {"statistics": parser.stats}
    if tab == "historico-de-partidas":
        cards = _HistoryParser(competition, season)
        cards.feed(page)
        if cards.matches:
            return {"matches": cards.matches}
        return {
            "matches": [{"match_id": key, "url": value} for key, value in parser.matches.items()]
        }
    for index, row in enumerate(parser.rows):
        if row[:3] == ["Nome", "Apelido", "Clube Atual"]:
            athletes = [
                {"name": item[0], "nickname": item[1], "current_club": item[2]}
                for item in parser.rows[index + 1 :]
                if len(item) >= 3 and item[0]
            ]
            return {"listed_athletes": athletes}
    raise CBFError("Aba de atletas sem a tabela esperada")


def _schema(connection: sqlite3.Connection) -> None:
    connection.execute("""CREATE TABLE IF NOT EXISTS cbf_teams (
        competition TEXT NOT NULL,
        season INTEGER NOT NULL,
        team_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        state TEXT,
        index_url TEXT NOT NULL,
        first_seen_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        PRIMARY KEY (competition, season, team_id)
    )""")
    connection.execute("""CREATE TABLE IF NOT EXISTS cbf_team_pages (
        id INTEGER PRIMARY KEY,
        url TEXT NOT NULL,
        competition TEXT NOT NULL,
        season INTEGER NOT NULL,
        team_id INTEGER,
        tab TEXT NOT NULL,
        sha256 TEXT NOT NULL,
        path TEXT NOT NULL,
        fetched_at TEXT NOT NULL,
        data_json TEXT NOT NULL,
        UNIQUE (url, sha256)
    )""")
    connection.execute(
        "CREATE INDEX IF NOT EXISTS cbf_team_pages_lookup ON cbf_team_pages (competition, season, team_id, tab)"
    )
    connection.execute("""CREATE TABLE IF NOT EXISTS cbf_team_unavailable (
        url TEXT PRIMARY KEY,
        competition TEXT NOT NULL,
        season INTEGER NOT NULL,
        team_id INTEGER NOT NULL,
        tab TEXT NOT NULL,
        status_code INTEGER NOT NULL CHECK (status_code = 404),
        observed_at TEXT NOT NULL
    )""")


class CBFTeamCollector(CBFCollector):
    def _cached(self, connection: sqlite3.Connection, url: str) -> bool:
        rows = connection.execute(
            "SELECT path FROM cbf_team_pages WHERE url = ? ORDER BY id DESC", (url,)
        ).fetchall()
        return any((self.root / path).is_file() for (path,) in rows)

    def _store(
        self,
        connection: sqlite3.Connection,
        *,
        url: str,
        competition: str,
        season: int,
        team_id: int | None,
        tab: str,
        body: bytes,
        parsed: dict,
    ) -> None:
        digest = hashlib.sha256(body).hexdigest()
        relative = Path("html") / f"{digest}.html"
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            temporary: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb", dir=target.parent, prefix=".cbf-", delete=False
                ) as stream:
                    temporary = Path(stream.name)
                    stream.write(body)
                    stream.flush()
                    os.fsync(stream.fileno())
                temporary.replace(target)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
        connection.execute(
            """INSERT OR IGNORE INTO cbf_team_pages
            (url, competition, season, team_id, tab, sha256, path, fetched_at, data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                url,
                competition,
                season,
                team_id,
                tab,
                digest,
                relative.as_posix(),
                datetime.now(UTC).isoformat(),
                json.dumps(parsed, ensure_ascii=False, separators=(",", ":")),
            ),
        )
        connection.execute("DELETE FROM cbf_team_unavailable WHERE url = ?", (url,))
        connection.commit()

    def _record_unavailable(
        self,
        connection: sqlite3.Connection,
        url: str,
        competition: str,
        season: int,
        team_id: int,
        tab: str,
    ) -> None:
        connection.execute(
            """INSERT INTO cbf_team_unavailable
            (url, competition, season, team_id, tab, status_code, observed_at)
            VALUES (?, ?, ?, ?, ?, 404, ?)
            ON CONFLICT (url) DO UPDATE SET observed_at=excluded.observed_at""",
            (url, competition, season, team_id, tab, datetime.now(UTC).isoformat()),
        )
        connection.commit()

    def _record_teams(
        self,
        connection: sqlite3.Connection,
        competition: str,
        season: int,
        url: str,
        teams: list[dict],
    ) -> None:
        observed_at = datetime.now(UTC).isoformat()
        for team in teams:
            connection.execute(
                """INSERT INTO cbf_teams
                (competition, season, team_id, name, state, index_url, first_seen_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (competition, season, team_id) DO UPDATE SET
                name=excluded.name, state=excluded.state,
                index_url=excluded.index_url, last_seen_at=excluded.last_seen_at""",
                (
                    competition,
                    season,
                    team["team_id"],
                    team["name"],
                    team["state"],
                    url,
                    observed_at,
                    observed_at,
                ),
            )
        connection.commit()

    def collect_teams(
        self,
        competitions: list[str],
        season: int,
        *,
        max_requests: int = 20,
        refresh: bool = False,
        retry_unavailable: bool = False,
        progress: Callable[[dict], None] | None = None,
    ) -> dict:
        if not 1 <= max_requests <= 10000:
            raise CBFError("max_requests deve estar entre 1 e 10000")
        selected = list(dict.fromkeys(competitions))
        for competition in selected:
            index_url(competition, season)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        result = {
            "season": season,
            "requests": 0,
            "indexes": 0,
            "team_pages": 0,
            "skipped": 0,
            "unavailable": 0,
        }
        with sqlite3.connect(self.database_path) as connection:
            _schema(connection)
            for competition in selected:
                url = index_url(competition, season)
                if refresh or not self._cached(connection, url):
                    if result["requests"] >= max_requests:
                        return result
                    body, _ = self._request(url, 5 * 1024 * 1024)
                    result["requests"] += 1
                    if b"<html" not in body[:1024].lower():
                        raise CBFError(f"Índice não retornou HTML: {url}")
                    teams = parse_index(body.decode("utf-8", errors="replace"), competition, season)
                    self._store(
                        connection,
                        url=url,
                        competition=competition,
                        season=season,
                        team_id=None,
                        tab="index",
                        body=body,
                        parsed={"teams": teams},
                    )
                    self._record_teams(connection, competition, season, url, teams)
                    result["indexes"] += 1
                    if progress:
                        progress(
                            {
                                "competition": competition,
                                "tab": "index",
                                "teams": len(teams),
                                **result,
                            }
                        )
                else:
                    result["skipped"] += 1
                    exists = connection.execute(
                        "SELECT 1 FROM cbf_teams WHERE competition = ? AND season = ? LIMIT 1",
                        (competition, season),
                    ).fetchone()
                    if not exists:
                        cached = connection.execute(
                            "SELECT data_json FROM cbf_team_pages WHERE url = ? ORDER BY id DESC LIMIT 1",
                            (url,),
                        ).fetchone()
                        if cached:
                            teams = json.loads(cached[0])["teams"]
                            self._record_teams(connection, competition, season, url, teams)
            for competition in selected:
                url = index_url(competition, season)
                teams = connection.execute(
                    "SELECT team_id FROM cbf_teams WHERE competition = ? AND season = ? ORDER BY team_id",
                    (competition, season),
                ).fetchall()
                if not teams:
                    raise CBFError(f"Índice sem clubes registrados: {competition}/{season}")
                for (team_id,) in teams:
                    for tab in TABS:
                        detail_url = f"{url}/{team_id}?tab={tab}"
                        if not refresh and self._cached(connection, detail_url):
                            result["skipped"] += 1
                            continue
                        if (
                            not refresh
                            and not retry_unavailable
                            and connection.execute(
                                "SELECT 1 FROM cbf_team_unavailable WHERE url = ?", (detail_url,)
                            ).fetchone()
                        ):
                            result["skipped"] += 1
                            result["unavailable"] += 1
                            continue
                        if result["requests"] >= max_requests:
                            return result
                        try:
                            body, _ = self._request(detail_url, 5 * 1024 * 1024)
                        except CBFNotFound:
                            result["requests"] += 1
                            result["unavailable"] += 1
                            self._record_unavailable(
                                connection, detail_url, competition, season, team_id, tab
                            )
                            if progress:
                                progress(
                                    {
                                        "competition": competition,
                                        "team_id": team_id,
                                        "tab": tab,
                                        "status": "unavailable_404",
                                        **result,
                                    }
                                )
                            continue
                        result["requests"] += 1
                        if b"<html" not in body[:1024].lower():
                            raise CBFError(f"Clube não retornou HTML: {detail_url}")
                        parsed = parse_detail(
                            body.decode("utf-8", errors="replace"), competition, season, tab
                        )
                        self._store(
                            connection,
                            url=detail_url,
                            competition=competition,
                            season=season,
                            team_id=team_id,
                            tab=tab,
                            body=body,
                            parsed=parsed,
                        )
                        result["team_pages"] += 1
                        if progress:
                            progress(
                                {
                                    "competition": competition,
                                    "team_id": team_id,
                                    "tab": tab,
                                    **result,
                                }
                            )
        return result


def team_coverage(database_path: Path, season: int) -> list[dict]:
    with sqlite3.connect(database_path) as connection:
        _schema(connection)
        rows = connection.execute(
            """SELECT t.competition, COUNT(DISTINCT t.team_id) AS teams,
            COUNT(DISTINCT CASE WHEN p.tab = 'atletas' THEN p.team_id END) AS athletes,
            COUNT(DISTINCT CASE WHEN p.tab = 'historico-de-partidas' THEN p.team_id END) AS history,
            COUNT(DISTINCT CASE WHEN p.tab = 'estatisticas' THEN p.team_id END) AS statistics
            FROM cbf_teams t LEFT JOIN cbf_team_pages p
              ON p.competition = t.competition AND p.season = t.season AND p.team_id = t.team_id
            WHERE t.season = ? GROUP BY t.competition ORDER BY t.competition""",
            (season,),
        ).fetchall()
    return [
        {
            "competition": comp,
            "teams": teams,
            "athletes": athletes,
            "history": history,
            "statistics": statistics,
        }
        for comp, teams, athletes, history, statistics in rows
    ]
