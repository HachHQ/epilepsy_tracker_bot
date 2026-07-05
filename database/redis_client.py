from redis.asyncio import Redis

from config_data.config import get_config

config = get_config(strict=False).redis

redis = Redis(
    host=config.host,
    port=config.port,
    db=config.db,
    decode_responses=False,
)