from dataclasses import dataclass
from functools import lru_cache

from environs import Env


@dataclass
class DatabaseConfig:
    db_name: str
    db_user: str
    db_password: str
    db_port: str
    db_host: str

@dataclass
class RedisConfig:
    host: str
    port: int
    db: int

@dataclass
class TgBot:
    token: str
    admins: list[int]
    hmac_secret_key: str

@dataclass
class Config:
    tg_bot: TgBot
    db: DatabaseConfig
    redis: RedisConfig

def load_config(path: str | None = None, *, strict: bool = True) -> Config:

    env: Env = Env()
    env.read_env(path)

    def get(name: str, default: str) -> str:
        return env(name) if strict else env(name, default)

    def get_admins() -> list[int]:
        if strict:
            return env.list('ADMINS', subcast=int)
        try:
            return env.list('ADMINS', subcast=int, default=[])
        except Exception:
            return []

    return Config(
        tg_bot=TgBot(
            token=get('API_TOKEN', 'missing-token'),
            admins=get_admins(),
            hmac_secret_key=get('HMAC_SECRET_KEY', 'dev-secret')
        ),
        db=DatabaseConfig(
            db_name=get('DB_NAME', 'diplomathesis'),
            db_user=get('DB_USER', 'postgres'),
            db_password=get('DB_PASSWORD', 'postgres'),
            db_port=get('DB_PORT', '5432'),
            db_host=get('DB_HOST', 'localhost')
        ),
        redis=RedisConfig(
            host=env('REDIS_HOST', 'localhost'),
            port=env.int('REDIS_PORT', 6379),
            db=env.int('REDIS_DB', 0),
        )
    )


@lru_cache(maxsize=2)
def get_config(*, strict: bool = True) -> Config:
    return load_config(".env", strict=strict)


def load_redis_config(path: str | None = None) -> RedisConfig:
    env: Env = Env()
    env.read_env(path)
    return RedisConfig(
        host=env('REDIS_HOST', 'localhost'),
        port=env.int('REDIS_PORT', 6379),
        db=env.int('REDIS_DB', 0),
    )