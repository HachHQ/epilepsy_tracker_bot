from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config_data.retention import SEIZURE_RETENTION_DAYS
from filters.correct_commands import ProfileIsSetCb
from handlers_logic.states_factories import ProfileForm
from i18n import t
from keyboards.menu_kb import get_cancel_kb
from keyboards.profile_form_kb import (
    get_ask_for_have_diagnosis_kb,
    get_commit_deleting_profile_kb,
    get_qeustion_about_species,
    get_sex_kb,
    get_submit_profile_settings_kb,
)
from services.redis_cache_data import (
    get_cached_current_profile,
    get_cached_login,
    get_cached_profiles_list,
)
from services.validators import (
    validate_age_of_profile_form,
    validate_less_than_30,
    validate_less_than_100,
    validate_name_of_profile_form,
)
from use_cases.profiles import (
    create_profile_from_form,
    delete_profile_record,
    get_profile,
    update_profile_field,
)

profile_form_router = Router()

def _profile_sex_label(sex: str) -> str:
    return t("profile.sex_male_label") if sex == "male" else t("profile.sex_female_label")

def get_profile_info(data: dict[str, str]) -> str:
    epilepsy_type = (
        t("profile.undefined_epilepsy")
        if data.get("type_of_epilepsy", None) is None
        else data["type_of_epilepsy"]
    )
    animal_line = ""
    if data.get("animal_species", None) is not None:
        animal_line = t("profile.animal_line", species=data["animal_species"])
    return t(
        "profile.summary",
        profile_name=data["profile_name"],
        epilepsy_type=epilepsy_type,
        age=data["age"],
        sex=_profile_sex_label(data["sex"]),
        animal_line=animal_line,
    )

@profile_form_router.callback_query(F.data == "to_filling_profile_form")
async def start_filling_profile_form(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    await state.clear()
    if await get_cached_login(db, callback.message.chat.id) is None:
        await state.clear()
        await callback.message.answer(t("profile.need_registration"))
        await callback.answer()
        return
    await callback.message.answer(t("profile.info_about_profile"), parse_mode="HTML")
    await callback.message.answer(t("profile.enter_profile_name"), reply_markup=get_cancel_kb())
    await state.set_state(ProfileForm.profile_name)
    await callback.answer()

@profile_form_router.message(StateFilter(ProfileForm.profile_name))
async def process_profile_name(message: Message, state: FSMContext):
    if validate_name_of_profile_form(message.text):
        await state.update_data(profile_name=message.text)
        await message.answer(t("profile.ask_human_profile"), reply_markup=get_qeustion_about_species())
        await state.set_state(ProfileForm.biological_species)
    else:
        await message.answer(t("profile.incorrect_profile_name"))

@profile_form_router.callback_query(F.data == "profile_for_human", StateFilter(ProfileForm.biological_species))
async def process_human_species(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(t("profile.ask_diagnosis"), reply_markup=get_ask_for_have_diagnosis_kb())
    await state.set_state(ProfileForm.type_of_epilepsy)
    await callback.answer()

@profile_form_router.callback_query(F.data == "profile_for_animal", StateFilter(ProfileForm.biological_species))
async def process_animal_species(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(t("profile.ask_animal_species"), reply_markup=get_cancel_kb())
    await callback.answer()

@profile_form_router.message(StateFilter(ProfileForm.biological_species))
async def process_profile_for_animal(message: Message, state: FSMContext):
    if validate_less_than_30(message.text):
        await state.update_data(animal_species=message.text)
        await message.answer(t("profile.ask_diagnosis"), reply_markup=get_ask_for_have_diagnosis_kb())
        await state.set_state(ProfileForm.type_of_epilepsy)
    else:
        await message.answer(t("profile.invalid_animal_species"), reply_markup=get_cancel_kb())


@profile_form_router.callback_query(F.data == "have_epilepsy_diagnosis",
                                    StateFilter(ProfileForm.type_of_epilepsy))
async def process_users_diagnosis(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(t("profile.enter_diagnosis"),
                                reply_markup=get_cancel_kb())
    await callback.answer()

@profile_form_router.callback_query(F.data == "dont_have_epilepsy_diagnosis",
                                    StateFilter(ProfileForm.type_of_epilepsy))
async def process_skip_user_diagnosis(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(t("profile.enter_age"),
                                reply_markup=get_cancel_kb())
    await state.set_state(ProfileForm.age)
    await callback.answer()

@profile_form_router.message(StateFilter(ProfileForm.type_of_epilepsy))
async def process_diagnosis(message: Message, state: FSMContext, db: AsyncSession):
    if validate_less_than_100(message.text):
        data = await state.get_data()
        mode = data.get("profmode", "create")
        if mode == 'prof_edit_mode':
            profile_id=data['profile_id']
            await update_profile_field(
                db, chat_id=message.chat.id, profile_id=int(profile_id),
                attribute='type_of_epilepsy', new_value=message.text,
            )
            await message.answer(t("profile.diagnosis_updated", value=message.text))
            await state.clear()
            return
        await state.update_data(type_of_epilepsy=message.text)
        await message.answer(t("profile.enter_age"),
                                reply_markup=get_cancel_kb())
        await state.set_state(ProfileForm.age)
    else:
        await message.answer(t("profile.invalid_diagnosis_length"))

@profile_form_router.message(StateFilter(ProfileForm.age))
async def process_age(message: Message, state: FSMContext, db: AsyncSession):
    if validate_age_of_profile_form(message.text):
        data = await state.get_data()
        mode = data.get("profmode", "create")
        if mode == 'prof_edit_mode':
            profile_id=data['profile_id']
            await update_profile_field(
                db, chat_id=message.chat.id, profile_id=int(profile_id),
                attribute='age', new_value=int(message.text),
            )
            await message.answer(t("profile.age_updated", value=message.text))
            await state.clear()
            return
        await state.update_data(age=message.text)
        await message.answer(t("profile.enter_sex"), reply_markup=get_sex_kb())
        await state.set_state(ProfileForm.sex)
    else:
        await message.answer(t("profile.incorrect_age"), parse_mode='HTML')

@profile_form_router.callback_query(F.data.in_({'sex_male', 'sex_female'}),
                                    StateFilter(ProfileForm.sex))
async def process_sex(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    mode = data.get("profmode", "create")
    if mode == 'prof_edit_mode':
        profile_id=data['profile_id']
        await update_profile_field(
            db, chat_id=callback.message.chat.id, profile_id=int(profile_id),
            attribute='sex', new_value=callback.data,
        )
        await callback.message.answer(
            t("profile.sex_updated_male") if callback.data == 'sex_male' else t("profile.sex_updated_female")
        )
        await callback.answer()
        await state.clear()
        return
    await state.update_data(sex=callback.data.split('_')[1])
    data = await state.get_data()
    profile_info = get_profile_info(data)
    await callback.message.answer(t("profile.form_completed"))
    await callback.message.answer(f"{profile_info}", parse_mode='HTML')
    await callback.message.answer(t("profile.form_confirm_prompt"),  reply_markup=get_submit_profile_settings_kb())
    await state.set_state(ProfileForm.check_form)
    await callback.answer()

@profile_form_router.callback_query(F.data == "submit_profile_settings", StateFilter(ProfileForm.check_form))
async def finish_filling_profile_data(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    data = await state.get_data()
    if not data:
        await callback.message.answer(t("profile.restart_registration"))
        await state.clear()
        await callback.answer()
        return
    result = await create_profile_from_form(db, chat_id=callback.message.chat.id, form_data=data)
    if not result.created:
        await callback.message.answer(t("profile.user_not_found"))
        await state.clear()
        await callback.answer()
        return

    await callback.message.answer(t("profile.created", name=result.profile_name))
    await state.clear()
    await callback.answer()

@profile_form_router.callback_query(ProfileIsSetCb(), F.data == 'prof_edit')
async def process_editing_profile_data(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    curr_profile = await get_cached_current_profile(db, callback.message.chat.id)
    profile_info = await get_profile(db, int(curr_profile.split("|")[0]))
    animal_line = ""
    if profile_info.biological_species is not None:
        animal_line = t("profile.animal_line", species=profile_info.biological_species)
    text = t(
        "profile.edit_view",
        name=curr_profile.split("|")[1],
        created_at=profile_info.created_at.date(),
        epilepsy_type=profile_info.type_of_epilepsy if profile_info.type_of_epilepsy is not None else t("profile.not_entered"),
        age=profile_info.age,
        sex=_profile_sex_label(profile_info.sex),
        animal_line=animal_line,
    )
    await callback.message.answer(text)
    await callback.answer()

@profile_form_router.message(F.text.startswith('/prof'))
async def process_editing_notify_settings(message: Message, state: FSMContext, db: AsyncSession):
    await state.clear()
    _, action = message.text.split('_', 1)
    curr_prof = await get_cached_current_profile(db, message.chat.id)
    if curr_prof is None:
        await message.answer(t("profile.choose_profile"))
    prof_info = await get_profile(db, int(curr_prof.split('|')[0]))
    if prof_info is None:
        await message.answer(t("profile.record_not_found"))
        return
    await state.update_data(profmode="prof_edit_mode", profile_id=int(curr_prof.split('|')[0]))
    if action == "eptype":
        await message.answer(t("profile.enter_diagnosis"))
        await state.set_state(ProfileForm.type_of_epilepsy)
    elif action == "age":
        await message.answer(t("profile.enter_age"))
        await state.set_state(ProfileForm.age)
    elif action == "sex":
        await message.answer(t("profile.enter_sex"), reply_markup=get_sex_kb())
        await state.set_state(ProfileForm.sex)
    elif action == "biospec":
        if prof_info.biological_species is not None:
            await message.answer(t("profile.enter_animal_species"))
            await state.set_state(ProfileForm.biological_species)
        else:
            await message.answer(t("profile.human_profile_only"))
    elif action == 'del':
        text = t("profile.delete_confirm", days=SEIZURE_RETENTION_DAYS)
        await message.answer(text, reply_markup=get_commit_deleting_profile_kb(int(curr_prof.split('|')[0])))
    else:
        await message.answer(t("profile.unknown_command"))

@profile_form_router.callback_query(F.data.startswith('delete_profile'))
async def process_deleting_profile(callback: CallbackQuery, db: AsyncSession):
    _, answer, prof_id = callback.data.split(":", 2)
    user_own_profiles = await get_cached_profiles_list(db, callback.message.chat.id)
    user_own_profiles = [prof['id'] for prof in user_own_profiles]
    if int(prof_id) not in user_own_profiles:
        await callback.message.answer(t("profile.delete_forbidden"))
        await callback.answer()
        return
    if answer == 'yes':
        result = await delete_profile_record(
            db, chat_id=callback.message.chat.id, profile_id=int(prof_id),
        )
        if result.deleted:
            await callback.message.answer(
                t(
                    "profile.delete_success",
                    seizures_preserved=result.seizures_preserved,
                    days=result.retention_days,
                )
            )
        else:
            await callback.message.answer(t("profile.delete_not_found"))
    else:
        await callback.message.answer(t("profile.delete_cancelled"))
