"""Extração conservadora de elencos e substituições em súmulas CBF já baixadas."""

import hashlib
import re
import shutil
import sqlite3
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote


class SumulaParseError(ValueError):
    """O layout não atende aos critérios de extração verificada."""


@dataclass(frozen=True)
class Word:
    x: float
    y: float
    text: str


def _key(value: str) -> str:
    plain = "".join(
        char
        for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]", "", plain)


def _words(page: ET.Element) -> list[Word]:
    return [
        Word(float(item.attrib["xMin"]), float(item.attrib["yMin"]), item.text or "")
        for item in page.iter("{http://www.w3.org/1999/xhtml}word")
    ]


def _at(words: list[Word], y: float, low: float, high: float) -> list[str]:
    return [word.text for word in words if abs(word.y - y) < 0.8 and low <= word.x < high]


def _roster(words: list[Word]) -> list[dict]:
    headings = [word.y for word in words if word.text == "Relação"]
    if len(headings) != 1:
        raise SumulaParseError("Cabeçalho da relação de jogadores ausente ou ambíguo")
    rows = []
    for word in words:
        if not headings[0] + 25 < word.y < 770 or not word.text.isdigit():
            continue
        if 250 <= word.x < 290:
            side, shirt_band, role_band = "home", (42, 58), (213, 232)
        elif 508 <= word.x < 545:
            side, shirt_band, role_band = "away", (298, 314), (470, 490)
        else:
            continue
        shirts = [item for item in _at(words, word.y, *shirt_band) if item.isdigit()]
        roles = [
            item for item in _at(words, word.y, *role_band) if item in {"T", "R", "T(g)", "R(g)"}
        ]
        if len(shirts) != 1 or len(roles) != 1:
            raise SumulaParseError(f"Linha de atleta ambígua em y={word.y:.1f}")
        rows.append(
            {
                "side": side,
                "shirt": int(shirts[0]),
                "cbf_person_id": int(word.text),
                "role": roles[0][0],
                "goalkeeper": "(g)" in roles[0],
            }
        )
    for side in ("home", "away"):
        members = [row for row in rows if row["side"] == side]
        if sum(row["role"] == "T" for row in members) != 11:
            raise SumulaParseError(f"Escalação titular incompleta para {side}")
        if len({row["shirt"] for row in members}) != len(members) or len(
            {row["cbf_person_id"] for row in members}
        ) != len(members):
            raise SumulaParseError(f"Camisa ou ID CBF duplicado para {side}")
    return rows


def _event_minute(period: str, clock: str, first_extra: int) -> int:
    if period == "INT" and clock == "-":
        return 45 + first_extra
    match = re.fullmatch(r"(\+?)(\d{1,2}):00", clock)
    if period not in {"1T", "2T"} or match is None:
        raise SumulaParseError(f"Tempo de substituição desconhecido: {period} {clock}")
    minute = int(match.group(2))
    if match.group(1):
        minute += 45
    elif not 0 <= minute <= 45:
        raise SumulaParseError(f"Minuto fora do período: {period} {clock}")
    return minute + (45 + first_extra if period == "2T" else 0)


def _substitutions(words: list[Word], teams: dict[str, str], first_extra: int) -> list[dict]:
    headings = [word.y for word in words if word.text == "Substituições"]
    if len(headings) != 1:
        raise SumulaParseError("Cabeçalho de substituições ausente ou ambíguo")
    events = []
    for word in words:
        if not headings[0] + 15 < word.y < 770 or not 90 <= word.x < 110:
            continue
        if word.text not in {"INT", "1T", "2T"}:
            continue
        clocks = _at(words, word.y, 48, 83)
        team_text = " ".join(_at(words, word.y, 113, 240))
        entered = [item for item in _at(words, word.y, 240, 255) if item.isdigit()]
        left = [item for item in _at(words, word.y, 397, 411) if item.isdigit()]
        if len(clocks) != 1 or len(entered) != 1 or len(left) != 1:
            raise SumulaParseError(f"Linha de substituição ambígua em y={word.y:.1f}")
        matching = [side for side, name in teams.items() if _key(name) == _key(team_text)]
        if len(matching) != 1:
            raise SumulaParseError(f"Equipe de substituição não reconhecida: {team_text}")
        events.append(
            {
                "side": matching[0],
                "period": word.text,
                "clock": clocks[0],
                "nominal_minute": _event_minute(word.text, clocks[0], first_extra),
                "in_shirt": int(entered[0]),
                "out_shirt": int(left[0]),
            }
        )
    return events


def _appearances(roster: list[dict], events: list[dict], duration: int) -> list[dict]:
    by_shirt = {(row["side"], row["shirt"]): row for row in roster}
    intervals: dict[tuple[str, int], list[int | None]] = {
        key: [0 if row["role"] == "T" else None, None] for key, row in by_shirt.items()
    }
    for event in sorted(events, key=lambda item: item["nominal_minute"]):
        incoming = (event["side"], event["in_shirt"])
        outgoing = (event["side"], event["out_shirt"])
        minute = event["nominal_minute"]
        if incoming not in by_shirt or outgoing not in by_shirt or not 0 <= minute <= duration:
            raise SumulaParseError("Substituição sem atleta correspondente ou fora da partida")
        if (
            intervals[incoming] != [None, None]
            or intervals[outgoing][0] is None
            or (intervals[outgoing][1] is not None)
        ):
            raise SumulaParseError(
                "Substituição contradiz titulares/reservas ou eventos anteriores"
            )
        intervals[incoming][0] = minute
        intervals[outgoing][1] = minute
        event["in_cbf_person_id"] = by_shirt[incoming]["cbf_person_id"]
        event["out_cbf_person_id"] = by_shirt[outgoing]["cbf_person_id"]
    result = []
    for key, row in sorted(by_shirt.items()):
        start, end = intervals[key]
        if start is None:
            played = 0
        else:
            played = (duration if end is None else end) - start
            if played < 0:
                raise SumulaParseError("Intervalo de participação negativo")
        result.append({**row, "nominal_minutes": played})
    return result


def parse_sumula(pdf: Path) -> dict:
    """Extrai apenas um layout A4 de três páginas reconhecido; falha fechado."""
    if shutil.which("pdftotext") is None:
        raise SumulaParseError("pdftotext (Poppler) não está instalado")
    try:
        bbox = subprocess.run(
            ["pdftotext", "-bbox", str(pdf), "-"],
            capture_output=True,
            check=True,
            timeout=30,
        ).stdout
        layout = subprocess.run(
            ["pdftotext", "-layout", str(pdf), "-"],
            capture_output=True,
            check=True,
            timeout=30,
        ).stdout.decode("utf-8")
        root = ET.fromstring(bbox)
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        UnicodeDecodeError,
        ET.ParseError,
    ) as error:
        raise SumulaParseError(f"Não foi possível ler a súmula: {error}") from error
    pages = list(root.iter("{http://www.w3.org/1999/xhtml}page"))
    if len(pages) != 3 or any(
        abs(float(page.attrib["width"]) - 595.276) > 2
        or abs(float(page.attrib["height"]) - 841.89) > 2
        for page in pages
    ):
        raise SumulaParseError("Layout de páginas CBF não reconhecido")
    first = layout.split("\f", 1)[0]
    game = re.search(r"^\s*Jogo:\s*(.+?)\s+X\s+(.+?)\s*$", first, flags=re.MULTILINE)
    competition = re.search(r"^\s*Campeonato:\s*(.+?)\s+Rodada:", first, flags=re.MULTILINE)
    additions = re.findall(r"Acréscimo:\s*(\d+)\s+min", first)
    publication = re.search(r"Publicação da Súmula:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})", first)
    game_number = re.search(r"Jogo:\s*(\d+)", first)
    match_date = re.search(r"\bData:\s*(\d{2}/\d{2}/\d{4})", first)
    if (
        not game
        or not competition
        or len(additions) != 2
        or not publication
        or not game_number
        or not match_date
    ):
        raise SumulaParseError("Metadados ou cronologia da súmula incompletos")
    if "NÃO HOUVE EXPULSÕES" not in layout.split("\f")[1]:
        raise SumulaParseError("Expulsões presentes ou não verificáveis; minutos exigem revisão")
    first_extra, second_extra = map(int, additions)
    if not 0 <= first_extra <= 30 or not 0 <= second_extra <= 30:
        raise SumulaParseError("Acréscimos fora do intervalo esperado")
    teams = {"home": game.group(1).strip(), "away": game.group(2).strip()}
    roster = _roster(_words(pages[0]))
    events = _substitutions(_words(pages[2]), teams, first_extra)
    if not events and "NÃO HOUVE SUBSTITUIÇÕES" not in layout.split("\f")[2]:
        raise SumulaParseError("Tabela de substituições não reconhecida")
    duration = 90 + first_extra + second_extra
    return {
        "competition_label": competition.group(1).strip(),
        "cbf_game_number": int(game_number.group(1)),
        "match_date_text": match_date.group(1),
        "teams": teams,
        "publication_local_text": publication.group(1),
        "first_half_extra": first_extra,
        "second_half_extra": second_extra,
        "nominal_duration": duration,
        "players": _appearances(roster, events, duration),
        "substitutions": events,
        "warning": "Minutos nominais usam acréscimos informados; nomes truncados não são extraídos.",
    }


def extract_stored_sumula(database: Path, document_id: int) -> dict:
    if document_id < 1 or not database.is_file():
        raise SumulaParseError("ID ou banco CBF inválido")
    with sqlite3.connect(f"file:{quote(str(database.resolve()))}?mode=ro", uri=True) as connection:
        row = connection.execute(
            "SELECT document_url, season, sha256, path, fetched_at FROM cbf_sumulas WHERE id=?",
            (document_id,),
        ).fetchone()
    if row is None:
        raise SumulaParseError("Súmula CBF não encontrada")
    document_url, season, digest, relative, fetched_at = row
    root = (database.parent / "cbf").resolve()
    target = (root / relative).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise SumulaParseError("Arquivo da súmula ausente ou fora do diretório CBF")
    if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        raise SumulaParseError("Hash da súmula não corresponde ao banco")
    result = parse_sumula(target)
    if f"/{season}" not in result["competition_label"]:
        raise SumulaParseError("Temporada da súmula diverge do banco")
    return {
        "document_id": document_id,
        "document_url": document_url,
        "season": season,
        "sha256": digest,
        "fetched_at": fetched_at,
        **result,
    }
