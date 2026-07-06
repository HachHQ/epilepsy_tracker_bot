from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from services.redis_cache_data import (
    get_cached_current_profile,
    get_cached_profile_triggers_list,
    get_cached_triggers_list,
)
from use_cases.seizures import update_seizure_field


def parse_callback_data(data: str) -> dict:
    result: dict = {}
    if ":" not in data:
        return {"type": "unknown", "raw": data}
    type_, *rest = data.split(":")
    result["type"] = type_
    if type_ == "year":
        if "/" in rest[0]:
            short_type, date = rest[0].split("/", 1)
            result.update({"value": short_type, "date": date})
        else:
            result["value"] = rest[0]
    elif type_ == "month":
        result["index"] = rest[0]
        result["name"] = rest[1]
    elif type_ == "day":
        result["value"] = rest[0]
    else:
        result["raw"] = data
    return result


def format_small_date_numbers(date: str) -> str:
    if 0 < int(date) < 10:
        return f"0{int(date)}"
    return date


async def get_action_btns_flag(state: FSMContext) -> bool:
    data = await state.get_data()
    return data.get("mode", "create") != "edit"


async def is_edit_mode(state: FSMContext) -> bool:
    data = await state.get_data()
    return data.get("mode") == "edit"


async def save_seizure_edit(
    db: AsyncSession,
    chat_id: int,
    state: FSMContext,
    attribute: str,
    new_value,
) -> None:
    data = await state.get_data()
    await update_seizure_field(
        db,
        user_id=chat_id,
        profile_id=int(data["profile_id"]),
        seizure_id=int(data["seizure_id"]),
        attribute=attribute,
        new_value=new_value,
    )


async def load_trigger_keyboard_options(db: AsyncSession, chat_id: int) -> list:
    current_profile = await get_cached_current_profile(db, chat_id)
    profile_id = int(current_profile.split("|", 1)[0])
    global_triggers = await get_cached_triggers_list(db, chat_id)
    profile_triggers = await get_cached_profile_triggers_list(db, chat_id, profile_id)
    return profile_triggers + global_triggers
