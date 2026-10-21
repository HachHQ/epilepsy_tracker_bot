from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.seizures import get_seizure_by_id, list_profile_seizures
from database.repositories.users import get_user_by_chat_id
from database.seizure_values import format_seizure_date, format_seizure_time
from handlers_logic.seizure_form.screen import FormScreen, FormTurn, answer, edit, turn
from handlers_logic.states_factories import SeizureForm
from i18n import t
from keyboards.seizure_kb import (
    generate_seizure_type_keyboard,
    get_count_of_seizures_kb,
    get_duration_kb,
    get_enrich_kb,
    get_review_kb,
    get_time_ranges_kb,
    get_year_date_kb,
)
from services.notes_formatters import get_minutes_and_seconds
from services.user_timezone import get_local_time_from_offset
from use_cases.medications import medication_text_on
from use_cases.seizures import build_seizure_date


async def user_local_now(db: AsyncSession, chat_id: int) -> datetime | None:
    user = await get_user_by_chat_id(db, chat_id)
    if user is None or not user.timezone:
        return None
    return get_local_time_from_offset(int(user.timezone))


async def apply_last_defaults(db: AsyncSession, profile_id: int | None, state) -> None:
    await state.update_data(count=1, from_last=False)
    if profile_id is None:
        return
    rows = await list_profile_seizures(db, profile_id, descending=True)
    if not rows:
        return
    last = rows[0]
    await state.update_data(
        type_of_seizure=last.type_of_seizure,
        severity=last.severity,
        triggers=last.triggers,
        from_last=bool(last.type_of_seizure or last.severity or last.triggers),
    )


def format_review(data: dict, medication: str | None = None) -> str:
    duration = data.get("duration")
    text = t(
        "seizure_form.review",
        date=data.get("date_short") or build_seizure_date(data),
        time=data.get("time_of_day") or "—",
        duration=get_minutes_and_seconds(duration) if duration is not None else "—",
        count=data.get("count") or 1,
        seizure_type=data.get("type_of_seizure") or t("seizure.not_filled"),
        severity=data.get("severity") or t("seizure.not_filled"),
        triggers=data.get("triggers") or t("seizure.not_filled"),
        medication=medication or t("notes.no_active_course"),
    )
    if data.get("from_last"):
        text += "\n\n" + t("seizure_form.copied_from_last")
    return text


def saved_caption(seizure, medication: str | None = None) -> str:
    return t(
        "seizure_form.saved_card",
        date=format_seizure_date(seizure.date) or "—",
        time=format_seizure_time(seizure.time) or "—",
        duration=get_minutes_and_seconds(seizure.duration) if seizure.duration is not None else "—",
        count=seizure.count or 1,
        seizure_type=seizure.type_of_seizure or t("seizure.not_filled"),
        severity=seizure.severity or t("seizure.not_filled"),
        triggers=seizure.triggers or t("seizure.not_filled"),
        symptoms=seizure.symptoms or t("seizure.not_filled"),
        comment=seizure.comment or t("seizure.not_filled"),
        location=seizure.location or t("seizure.not_filled"),
        video=t("seizure_form.video_yes") if seizure.video_tg_id else t("seizure.not_filled"),
        medication=medication or t("notes.no_active_course"),
    )


async def review_turn(state, db: AsyncSession, *, edit_message: bool) -> FormTurn:
    data = await state.get_data()
    medication = await medication_text_on(
        db,
        data.get("profile_id"),
        data.get("date_short") or build_seizure_date(data),
    )
    await state.set_state(SeizureForm.review)
    screen = edit if edit_message else answer
    return turn(
        screen(
            format_review(data, medication),
            reply_markup=get_review_kb(back=data.get("phase") != "live"),
        ),
        ack=edit_message,
    )


async def date_step_turn(db: AsyncSession, chat_id: int, *, edit_message: bool) -> FormTurn:
    local_now = await user_local_now(db, chat_id)
    screen = edit if edit_message else answer
    return turn(
        screen(
            t("seizure_form.select_year_or_date"),
            reply_markup=get_year_date_kb(today=local_now),
            parse_mode="HTML",
        ),
        ack=edit_message,
    )


async def time_step_turn(db: AsyncSession, chat_id: int, *, edit_message: bool) -> FormTurn:
    local_now = await user_local_now(db, chat_id)
    screen = edit if edit_message else answer
    return turn(
        screen(
            t("seizure_form.enter_time"),
            reply_markup=get_time_ranges_kb(action_btns=False, local_dt=local_now, back=True),
        ),
        ack=edit_message,
    )


def duration_step_turn(*, edit_message: bool) -> FormTurn:
    screen = edit if edit_message else answer
    return turn(
        screen(
            t("seizure_form.select_duration"),
            reply_markup=get_duration_kb(action_btns=False, back=True),
        ),
        ack=edit_message,
    )


def saved_from_preview(preview, medication: str | None = None) -> str:
    return t(
        "seizure_form.saved_card",
        date=preview.date or "—",
        time=preview.time or "—",
        duration=preview.duration or "—",
        count=preview.count or 1,
        seizure_type=preview.type_of_seizure or t("seizure.not_filled"),
        severity=preview.severity or t("seizure.not_filled"),
        triggers=preview.triggers or t("seizure.not_filled"),
        symptoms=preview.symptoms or t("seizure.not_filled"),
        comment=preview.comment or t("seizure.not_filled"),
        location=preview.location or t("seizure.not_filled"),
        video=t("seizure_form.video_yes") if preview.video_tg_id else t("seizure.not_filled"),
        medication=medication or t("notes.no_active_course"),
    )


async def open_passed_form(state, db: AsyncSession, chat_id: int, profile_id: int | None) -> FormTurn:
    await state.clear()
    await apply_last_defaults(db, profile_id, state)
    await state.update_data(phase="capture", profile_id=profile_id)
    await state.set_state(SeizureForm.year)
    return await date_step_turn(db, chat_id, edit_message=True)


async def open_type_picker(state) -> FormTurn:
    await state.update_data(return_to_review=True)
    await state.set_state(SeizureForm.type_of_seizure)
    return turn(
        edit(
            t("seizure_form.select_type"),
            reply_markup=generate_seizure_type_keyboard(0, 6, action_btns=False, back=True),
        ),
        ack=True,
    )


async def open_count_picker(state) -> FormTurn:
    await state.update_data(return_to_review=True)
    await state.set_state(SeizureForm.count)
    return turn(
        edit(
            t("seizure_form.select_count"),
            reply_markup=get_count_of_seizures_kb(action_btns=False, back=True),
        ),
        ack=True,
    )


async def handle_back(state, db: AsyncSession, chat_id: int) -> FormTurn:
    current = await state.get_state()
    data = await state.get_data()
    if data.get("return_to_review"):
        await state.update_data(return_to_review=False)
        return await review_turn(state, db, edit_message=True)
    if current == SeizureForm.review.state and data.get("phase") != "live":
        await state.set_state(SeizureForm.duration)
        return duration_step_turn(edit_message=True)
    if current == SeizureForm.duration.state:
        await state.set_state(SeizureForm.hour)
        return await time_step_turn(db, chat_id, edit_message=True)
    if current == SeizureForm.hour.state:
        await state.set_state(SeizureForm.year)
        return await date_step_turn(db, chat_id, edit_message=True)
    return turn(ack=True)


async def finish_edit(state, db: AsyncSession, fallback: FormScreen, *, ack: bool) -> FormTurn:
    data = await state.get_data()
    enrich = bool(data.get("enrich"))
    seizure_id = data.get("seizure_id")
    profile_id = data.get("profile_id")
    await state.clear()
    if enrich and seizure_id and profile_id:
        seizure = await get_seizure_by_id(db, int(seizure_id), int(profile_id))
        if seizure is not None:
            medication = await medication_text_on(db, seizure.profile_id, seizure.date)
            screen = edit if fallback.edit else answer
            return turn(
                screen(saved_caption(seizure, medication), reply_markup=get_enrich_kb(seizure.id)),
                ack=ack,
            )
    return turn(fallback, ack=ack)
