import logging
from unittest.mock import AsyncMock, patch

import pytest

from database import redis_query


@pytest.mark.asyncio
async def test_delete_redis_cached_login_logs_info_when_key_removed(caplog: pytest.LogCaptureFixture) -> None:
    with patch.object(redis_query.redis, "delete", AsyncMock(return_value=1)):
        with caplog.at_level(logging.INFO):
            await redis_query.delete_redis_cached_login(42)

    assert "deleted from Redis" in caplog.text
    assert "42" in caplog.text


@pytest.mark.asyncio
async def test_delete_redis_cached_login_logs_debug_when_key_missing(caplog: pytest.LogCaptureFixture) -> None:
    with patch.object(redis_query.redis, "delete", AsyncMock(return_value=0)):
        with caplog.at_level(logging.DEBUG):
            await redis_query.delete_redis_cached_login(42)

    assert "not found in Redis" in caplog.text
