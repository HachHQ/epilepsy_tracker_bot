from database.redis_client import redis

async def get_cached_login(user_id: int) -> str:
    """Получает логин из кэша или None, если логина нет"""
    return await redis.get(f"user:login:{user_id}")

async def set_cached_login(user_id: int, login: str):
    """Сохраняет логин пользователя в Redis на 5 минут"""
    await redis.setex(f"user:login:{user_id}", 300, login)