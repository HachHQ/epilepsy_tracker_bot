from unittest.mock import AsyncMock, patch

import pytest

from database.models import Profile, User
from database.repositories.profiles import get_active_profile_by_id
from use_cases.profiles import (
    create_profile_from_form,
    switch_current_profile,
    update_profile_field,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_create_profile_from_form(db_session, test_user) -> None:
    with patch("use_cases.profiles.sync_user_own_profiles_cache", new=AsyncMock()):
        result = await create_profile_from_form(
            db_session,
            chat_id=test_user["chat_id"],
            form_data={
                "profile_name": "Secondary",
                "age": 28,
                "sex": "female",
                "type_of_epilepsy": "focal",
            },
        )

    assert result.created is True
    assert result.profile_name == "Secondary"


@pytest.mark.asyncio
async def test_update_profile_field_persists(db_session, test_user) -> None:
    with patch("use_cases.profiles.sync_user_own_profiles_cache", new=AsyncMock()):
        updated = await update_profile_field(
            db_session,
            chat_id=test_user["chat_id"],
            profile_id=test_user["profile"].id,
            attribute="age",
            new_value=31,
        )

    assert updated is not None
    assert updated.age == 31

    reloaded = await get_active_profile_by_id(db_session, test_user["profile"].id)
    assert reloaded.age == 31


@pytest.mark.asyncio
async def test_switch_current_profile_updates_user(db_session, test_user) -> None:
    with patch("use_cases.profiles.set_redis_cached_current_profile", new=AsyncMock()):
        second = test_user["profile"].__class__(
            user_id=test_user["user"].id,
            profile_name="Other",
            age=20,
            sex="male",
        )
        db_session.add(second)
        await db_session.flush()

        result = await switch_current_profile(
            db_session,
            chat_id=test_user["chat_id"],
            profile_id=second.id,
            profile_name=second.profile_name,
        )

    assert result.switched is True
    user = await db_session.get(User, test_user["user"].id)
    assert user.current_profile == second.id
