from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LogWriter:
    path: Path

    def write(self, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp}] {message}\n")


def build_log_path(shared_root: Path, start_ts: int | None = None) -> Path:
    now = time.localtime(start_ts or int(time.time()))
    year = f"{now.tm_year:04d}"
    month = f"{now.tm_mon:02d}"
    day = f"{now.tm_mday:02d}"
    ts = start_ts or int(time.time())
    return shared_root / "logs" / year / month / day / f"file{ts}.log"


def create_log_writer(shared_root: Path) -> LogWriter:
    start_ts = int(time.time())
    path = build_log_path(shared_root, start_ts)
    return LogWriter(path)
