import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config_data.config import load_config
from database.models import Profile, Seizure, User
from services.keyword_hasher import KeywordHasher


def _database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if url:
        return url

    from config_data.config import load_config

    cfg = load_config(".env", strict=False)
    return (
        f"postgresql+asyncpg://{cfg.db.db_user}:{cfg.db.db_password}"
        f"@{cfg.db.db_host}:{cfg.db.db_port}/{cfg.db.db_name}"
    )


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine(_database_url(), pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        await engine.dispose()
        pytest.skip(f"PostgreSQL unavailable: {exc}")

    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()

    await engine.dispose()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> dict:
    suffix = uuid.uuid4().hex[:8]
    chat_id = int(uuid.uuid4().int % 900_000_000) + 100_000_000
    user = User(
        telegram_id=chat_id,
        login=f"test_{suffix}",
        keyword_hash=KeywordHasher().hash_keyword("test"),
        name="Integration Test",
    )
    db_session.add(user)
    await db_session.flush()

    profile = Profile(
        user_id=user.id,
        profile_name=f"Profile_{suffix}",
        age=30,
        sex="male",
    )
    db_session.add(profile)
    await db_session.flush()
    user.current_profile = profile.id
    await db_session.flush()

    return {
        "user": user,
        "profile": profile,
        "chat_id": chat_id,
        "profile_key": f"{profile.id}|{profile.profile_name}",
    }
