from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

HEARTBEAT_PATH = Path(
    os.getenv("BOT_HEARTBEAT_PATH", str(Path(tempfile.gettempdir()) / "bot_heartbeat"))
)
HEARTBEAT_MAX_AGE_SECONDS = 60


def write_heartbeat(path: Path | None = None) -> None:
    target = path or HEARTBEAT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{time.time()}\n", encoding="utf-8")


def heartbeat_is_fresh(
    path: Path | None = None,
    *,
    max_age_seconds: float = HEARTBEAT_MAX_AGE_SECONDS,
    now: float | None = None,
) -> bool:
    target = path or HEARTBEAT_PATH
    try:
        written_at = target.stat().st_mtime
    except OSError:
        return False
    moment = time.time() if now is None else now
    return moment - written_at <= max_age_seconds
