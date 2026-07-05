from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from filters.correct_commands import IsAdmin


@pytest.mark.asyncio
async def test_is_admin_allows_configured_admin() -> None:
    message = MagicMock()
    message.from_user.id = 466024868
    config = SimpleNamespace(tg_bot=SimpleNamespace(admins=[466024868, 123]))

    with patch("filters.correct_commands.get_config", return_value=config):
        assert await IsAdmin()(message) is True


@pytest.mark.asyncio
async def test_is_admin_rejects_non_admin() -> None:
    message = MagicMock()
    message.from_user.id = 999
    config = SimpleNamespace(tg_bot=SimpleNamespace(admins=[466024868]))

    with patch("filters.correct_commands.get_config", return_value=config):
        assert await IsAdmin()(message) is False
