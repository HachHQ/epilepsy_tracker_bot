from sqlalchemy.future import select

from database.redis_client import redis
from database.db_init import SessionLocal
from database.models import User, Profile



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
                    return login
                login = user.login
            await set_cached_login(user_id, login)
            print("from db")
            return login
        except Exception as e:
            print(f"Неизвестная ошибка: {e}")
            return None

async def set_cached_login(user_id: int, login: str):
    await redis.setex(f"user:login:{user_id}", 3600, login)

async def delete_cached_login(user_id: int):
    key = f"user:login:{user_id}"
    deleted = await redis.delete(key)
    if deleted:
        print(f"Логин пользователя с ID {user_id} успешно удален из Redis.")
    else:
        print(f"Логин пользователя с ID {user_id} не найден в Redis.")

async def get_cached_current_profile(user_id: int) -> str:
    profile_key = f"user:current_profile:{user_id}"
    current_profile = await redis.get(profile_key)

    if current_profile:
        print("Текущий профиль получен из Redis")
        return current_profile.decode('utf-8')
    try:
        async with SessionLocal() as db:
            result = await db.execute(select(User).filter(User.telegram_id == user_id))
            user = result.scalars().first()
            search_profile_name = await db.execute(select(Profile).filter(Profile.id == user.current_profile))
            profile = search_profile_name.scalars().first()
            if not user.current_profile:
                print("Профиль null")
                profile = "Не выбран"
                return profile
            if not profile:
                print("Профиль не существует")
                profile = "Профиль не существует"
                return profile
            if not user:
                print("Пользователь не зарегестрирован")
                login = "Не зарегистрирован"
                return login
            await set_cached_current_profile(user_id, user.current_profile, profile.profile_name)
            print("Текущий профиль получен из базы данных")
            return f"{user.current_profile}|{profile.profile_name}"
    except Exception as e:
        print(f"Ошибка при получении текущего профиля: {e}")
        return None

async def set_cached_current_profile(user_id: int, profile_id: int, profile_name: str):
    profile_key = f"user:current_profile:{user_id}"
    await redis.setex(profile_key, 3600, f"{profile_id}|{profile_name}")
    print(f"Текущий профиль '{profile_name}' сохранен в Redis")


async def clear_cached_current_profile(user_id: int):
    profile_key = f"user:current_profile:{user_id}"
    deleted = await redis.delete(profile_key)
    if deleted:
        print(f"Текущий профиль пользователя с ID {user_id} удален из Redis")
    else:
        print(f"Текущий профиль пользователя с ID {user_id} не найден в Redis")