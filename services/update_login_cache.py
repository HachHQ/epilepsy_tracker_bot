from database.redis_client import redis

async def get_cached_login(user_id: int) -> str:
    login = await redis.get(f"user:login:{user_id}")
    return login.decode("utf-8") if login else None

async def set_cached_login(user_id: int, login: str):
    await redis.setex(f"user:login:{user_id}", 300, login)