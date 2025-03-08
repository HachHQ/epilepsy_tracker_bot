from sqlalchemy.future import select

from database.redis_client import redis
from database.db_init import SessionLocal
from database.models import User



async def get_cached_login(user_id: int) -> str:
    login = await redis.get(f"user:login:{user_id}")
    if login:
        print("from redis")
        return login.decode('utf-8')
    if login == None:
        try:
            async with SessionLocal() as db:
                result = await db.execute(select(User).filter(User.telegram_id == user_id))
                user = result.scalars().first()
                if not user:
                    print("Пользователь не зарегестрирован")
                    login = "Не зарегистрирован"
                    return
                login = user.login
            await set_cached_login(user_id, login)
            print("from db")
            return login
        except Exception as e:
            print(f"Неизвестная ошибка: {e}")

async def set_cached_login(user_id: int, login: str):
    await redis.setex(f"user:login:{user_id}", 3600, login)
