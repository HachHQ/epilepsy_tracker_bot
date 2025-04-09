from dataclasses import dataclass
from environs import Env

@dataclass
class DatabaseConfig:
    db_name: str
    db_user: str
    db_password: str
    db_port: str
    db_host: str

@dataclass
class TgBot:
    token: str
    admins: str

@dataclass
class Config:
    tg_bot: TgBot
    db: DatabaseConfig

def load_config(path: str | None = None) -> Config:

    env: Env = Env()
    env.read_env(path)

    return Config(
        tg_bot=TgBot(
            token=env('API_TOKEN'),
            admins=env('ADMINS')
        ),
        db=DatabaseConfig(
            db_name=env('DB_NAME'),
            db_user=env('DB_USER'),
            db_password=env('DB_PASSWORD'),
            db_port=env('DB_PORT'),
            db_host=env('DB_HOST')
        )
    )