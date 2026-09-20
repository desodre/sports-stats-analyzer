"""Download and inspect a permitted YouTube video without adding media to Git."""

import hashlib
import json
import math
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse


class VideoError(ValueError):
    """A requested video operation could not be completed."""


VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
MEDIA_SUFFIXES = {".mp4", ".mkv", ".webm", ".mov"}


def youtube_video_id(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in YOUTUBE_HOSTS:
        raise VideoError("Informe uma URL HTTPS de vídeo do YouTube.")
    if parsed.hostname == "youtu.be":
        identifier = parsed.path.removeprefix("/")
    elif parsed.path == "/watch":
        identifier = parse_qs(parsed.query).get("v", [""])[0]
    elif parsed.path.startswith(("/shorts/", "/live/", "/embed/")):
        identifier = parsed.path.split("/")[2]
    else:
        identifier = ""
    if not VIDEO_ID.fullmatch(identifier):
        raise VideoError("A URL não contém um ID de vídeo válido.")
    return identifier


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, capture_output=True, text=True, check=True)
    except FileNotFoundError as error:
        raise VideoError(f"Comando ausente: {args[0]}") from error
    except subprocess.CalledProcessError as error:
        message = (error.stderr or error.stdout or "falha sem detalhes").strip()
        raise VideoError(f"{args[0]} falhou: {message[-1000:]}") from error


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_video(url: str, output_dir: Path) -> dict:
    """Download one public video at up to 720p and write a minimal provenance file."""
    identifier = youtube_video_id(url)
    if shutil.which("yt-dlp") is None or shutil.which("ffmpeg") is None:
        raise VideoError("Instale as dependências do projeto e ffmpeg antes de baixar vídeos.")
    if shutil.which("node") is None:
        raise VideoError("Node.js 22 ou superior é necessário para vídeos do YouTube.")
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    canonical_url = f"https://www.youtube.com/watch?v={identifier}"
    yt_dlp = ["yt-dlp", "--ignore-config", "--js-runtimes", "node", "--no-playlist"]
    metadata = json.loads(_run([*yt_dlp, "--dump-single-json", canonical_url]).stdout)
    if metadata.get("id") != identifier:
        raise VideoError("O ID retornado pelo provedor não corresponde à URL pedida.")
    result = _run(
        [
            *yt_dlp,
            "--continue",
            "--no-overwrites",
            "--max-filesize",
            "750M",
            "--format",
            "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "--merge-output-format",
            "mp4",
            "--output",
            str(output_dir / "%(id)s.%(ext)s"),
            "--print",
            "after_move:filepath",
            canonical_url,
        ]
    )
    candidates = [
        path
        for path in output_dir.glob(f"{identifier}.*")
        if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES
    ]
    printed = [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]
    selected = next((path for path in printed if path in candidates), None)
    if selected is None and len(candidates) == 1:
        selected = candidates[0]
    if selected is None:
        raise VideoError("Download terminou, mas o arquivo de vídeo não foi identificado.")
    record = {
        "source_url": canonical_url,
        "video_id": identifier,
        "title": metadata.get("title"),
        "channel": metadata.get("channel") or metadata.get("uploader"),
        "duration_s": metadata.get("duration"),
        "upload_date": metadata.get("upload_date"),
        "downloaded_at": datetime.now(UTC).isoformat(),
        "path": str(selected),
        "size_bytes": selected.stat().st_size,
        "sha256": _sha256(selected),
    }
    (output_dir / f"{identifier}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return record


def inspect_video(path: Path) -> dict:
    """Return duration and stream information from a local video file."""
    path = path.expanduser().resolve()
    if not path.is_file():
        raise VideoError(f"Vídeo não encontrado: {path}")
    probe = json.loads(
        _run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,codec_name,width,height",
                "-of",
                "json",
                str(path),
            ]
        ).stdout
    )
    try:
        duration = float(probe["format"]["duration"])
    except (KeyError, ValueError, TypeError) as error:
        raise VideoError("Não foi possível ler a duração do vídeo.") from error
    if duration <= 0 or not any(s.get("codec_type") == "video" for s in probe.get("streams", [])):
        raise VideoError("Arquivo sem fluxo de vídeo válido.")
    return {"path": str(path), "duration_s": duration, "streams": probe["streams"]}


def extract_frames(path: Path, output_dir: Path, every_s: int = 5) -> dict:
    """Extract timestamped JPEGs for local review without sending frames anywhere."""
    if every_s < 1 or every_s > 60:
        raise VideoError("O intervalo entre quadros deve estar entre 1 e 60 segundos.")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise VideoError("Instale ffmpeg e ffprobe antes de extrair quadros.")
    info = inspect_video(path)
    count = min(1000, math.ceil(info["duration_s"] / every_s))
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for index in range(count):
        second = index * every_s
        frame = output_dir / f"t{second:06d}s.jpg"
        if not frame.is_file():
            _run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-ss",
                    str(second),
                    "-i",
                    info["path"],
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=960:-2",
                    "-q:v",
                    "4",
                    "-y",
                    str(frame),
                ]
            )
        if frame.is_file() and frame.stat().st_size > 0:
            frames.append({"time_s": second, "path": str(frame)})
    manifest = {**info, "sample_interval_s": every_s, "frames": frames}
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "video": info["path"],
        "duration_s": info["duration_s"],
        "frame_count": len(frames),
        "manifest": str(output_dir / "manifest.json"),
    }
