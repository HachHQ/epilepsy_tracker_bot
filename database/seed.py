"""Idempotent minimal database seed for local development."""

from __future__ import annotations

import asyncio
import logging
import os

from sqlalchemy import select

from database.db_init import SessionLocal
from database.models import Profile, User
from services.keyword_hasher import KeywordHasher

logger = logging.getLogger(__name__)

DEFAULT_TELEGRAM_ID = 466024868
DEFAULT_LOGIN = "arthur"
DEFAULT_NAME = "Arthur"
DEFAULT_TIMEZONE = "+7"
DEFAULT_KEYWORD = "devseed123"
DEFAULT_PROFILE_NAME = "Основной"


async def seed_minimal_user() -> bool:
    telegram_id = int(os.getenv("SEED_TELEGRAM_ID", DEFAULT_TELEGRAM_ID))

    async with SessionLocal() as session:
        existing = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        if existing.scalars().first():
            logger.info("Seed skipped: user telegram_id=%s already exists", telegram_id)
            return False

        keyword = os.getenv("SEED_KEYWORD", DEFAULT_KEYWORD)
        user = User(
            telegram_id=telegram_id,
            telegram_username=None,
            telegram_fullname="Owner",
            name=os.getenv("SEED_NAME", DEFAULT_NAME),
            login=os.getenv("SEED_LOGIN", DEFAULT_LOGIN),
            timezone=os.getenv("SEED_TIMEZONE", DEFAULT_TIMEZONE),
            keyword_hash=KeywordHasher().hash_keyword(keyword),
        )
        session.add(user)
        await session.flush()

        profile = Profile(
            user_id=user.id,
            profile_name=os.getenv("SEED_PROFILE_NAME", DEFAULT_PROFILE_NAME),
            type_of_epilepsy=None,
            age=25,
            sex="male",
            biological_species="human",
        )
        session.add(profile)
        await session.flush()

        user.current_profile = profile.id
        await session.commit()

        logger.info(
            "Seed created user id=%s telegram_id=%s login=%s profile_id=%s",
            user.id,
            telegram_id,
            user.login,
            profile.id,
        )
        return True


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    await seed_minimal_user()


if __name__ == "__main__":
    asyncio.run(main())
