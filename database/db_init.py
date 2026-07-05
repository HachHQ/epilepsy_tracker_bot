import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config_data.config import get_config

config = get_config(strict=False)
logger = logging.getLogger(__name__)

DATABASE_URL = f"postgresql+asyncpg://{config.db.db_user}:{config.db.db_password}@{config.db.db_host}:{config.db.db_port}/{config.db.db_name}"

engine = create_async_engine(DATABASE_URL)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase): pass

async def init_db():
    import database.models  # noqa: F401

    logger.info("Database metadata loaded; apply schema changes with Alembic migrations")

if __name__ == "__main__":
    asyncio.run(init_db())
