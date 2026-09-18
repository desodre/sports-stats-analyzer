"""Coordenação Linux/macOS por credencial e diretório compartilhado."""

import fcntl
import hashlib
import time
from pathlib import Path

from sports_stats_analyzer.config import Settings


class RateGate:
    def __init__(self, token: str, interval: float, directory: Path | None = None):
        root = directory or Settings().sports_rate_limit_dir
        self.path = root / (hashlib.sha256(token.encode()).hexdigest() + ".lock")
        self.interval = interval
        self.next_allowed = 0.0

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.stream = self.path.open("a+")
        fcntl.flock(self.stream, fcntl.LOCK_EX)
        self.stream.seek(0)
        try:
            self.next_allowed = float(self.stream.read() or 0)
            delay = max(0, self.next_allowed - time.time())
            if delay > 60:
                raise ValueError("Cota aguardando liberação; repita a atualização mais tarde")
            time.sleep(delay)
            self.next_allowed = time.time() + self.interval
        except BaseException:
            self.stream.close()
            raise
        return self

    def defer(self, seconds: float):
        self.next_allowed = max(self.next_allowed, time.time() + seconds)

    def __exit__(self, *_):
        try:
            self.stream.seek(0)
            self.stream.truncate()
            self.stream.write(str(self.next_allowed))
            self.stream.flush()
        finally:
            fcntl.flock(self.stream, fcntl.LOCK_UN)
            self.stream.close()
