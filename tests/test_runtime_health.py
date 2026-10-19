import time
from pathlib import Path

from services.runtime_health import heartbeat_is_fresh, write_heartbeat


def test_missing_heartbeat_is_not_fresh(tmp_path: Path) -> None:
    assert heartbeat_is_fresh(tmp_path / "missing") is False


def test_fresh_heartbeat_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "bot_heartbeat"
    write_heartbeat(path)
    assert heartbeat_is_fresh(path, now=time.time()) is True


def test_stale_heartbeat_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bot_heartbeat"
    write_heartbeat(path)
    assert heartbeat_is_fresh(path, max_age_seconds=30, now=time.time() + 31) is False
