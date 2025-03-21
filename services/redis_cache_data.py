import json
from sqlalchemy.future import select
from database.redis_client import redis
from database.db_init import SessionLocal
from database.models import User, Profile, TrustedPersonProfiles



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

async def get_cached_user_id_from_db(user_id: int) -> int:
    user_db_id = await redis.get(f"user:user_db_id:{user_id}")
    if user_db_id:
        print("from redis")
        return user_db_id.decode('utf-8')
    if user_db_id == None:
        try:
            async with SessionLocal() as db:
                result = await db.execute(select(User).filter(User.telegram_id == user_id))
                user = result.scalars().first()
                if not user:
                    print("Пользователь не зарегестрирован")
                    user_db_id = "Не зарегистрирован"
                    return user_db_id
                user_db_id = user.id
                await set_cached_user_id_from_db(user_id, user_db_id)
                print("from db")
                return user_db_id
        except Exception as e:
            print(f"Неизвестная ошибка: {e}")
            return None

async def set_cached_user_id_from_db(user_id: int, user_db_id: int):
        await redis.setex(f"user:user_db_id:{user_id}", 3600, user_db_id)

async def clear_cached_user_id_from_db(user_id: int):
    profile_key = f"user:user_db_id:{user_id}"
    deleted = await redis.delete(profile_key)
    if deleted:
        print(f"Текущий профиль пользователя с ID {user_id} удален из Redis")
    else:
        print(f"Текущий профиль пользователя с ID {user_id} не найден в Redis")

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
            if user.current_profile == None:
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

async def get_cached_profiles_list(user_id: int, profile_type: str = "user_own") -> list[str]:
    cache_key = f"profiles:{user_id}:{profile_type}"
    cached_profiles = await redis.get(cache_key)
    if cached_profiles:
        profiles = json.loads(cached_profiles.decode('utf-8'))

        return profiles
    if not cached_profiles:
        try:
            async with SessionLocal() as db:
                if profile_type == "trusted":
                    query = (
                        select(Profile)
                        .join(TrustedPersonProfiles, Profile.id == TrustedPersonProfiles.profile_id)
                        .join(User, TrustedPersonProfiles.trusted_person_user_id == User.id)
                        .where(User.telegram_id == user_id)
                    )
                elif profile_type == "user_own":
                    redis_login = await get_cached_login(user_id)
                    query = (
                        select(Profile)
                        .join(User)
                        .where(User.login == redis_login)
                    )
                profiles_result = await db.execute(query)
                profiles = [profile.to_dict() for profile in profiles_result.scalars().all()]
                if not profiles:
                    print("У этого пользователя нет профилей")
                    return None
                await set_cached_profiles_list(user_id=user_id, profile_type=profile_type, profiles=profiles)
                return profiles
        except Exception as e:
            print(f"Ошибка при получении текущего профиля: {e}")
            return None

async def set_cached_profiles_list(user_id: int, profile_type: str, profiles):
    await redis.setex(f"profiles:{user_id}:{profile_type}", 3600, json.dumps(profiles))

async def clear_cached_profiles_list(user_id: int):
    profile_key = f"user:current_profile:{user_id}"
    deleted = await redis.delete(profile_key)
    if deleted:
        print(f"Текущий профиль пользователя с ID {user_id} удален из Redis")
    else:
        print(f"Текущий профиль пользователя с ID {user_id} не найден в Redis")