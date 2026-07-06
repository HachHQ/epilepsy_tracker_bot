import logging
from sqlalchemy import select, update, delete, asc, desc, cast, Date, func, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload
from datetime import datetime, date

from database.models import (MedicationCourse, User, Profile, RequestStatus, TrustedPersonProfiles,
                              TrustedPersonRequest, Seizure, SeizureSymptom, SeizureTrigger, Symptom, Trigger)
from database.repositories.medications import (
    create_medication_course as _create_medication_course,
    delete_medication as _delete_medication,
    get_medication_by_id as _get_medication_by_id,
    list_profile_medications as _list_profile_medications,
    update_medication_attribute as _update_medication_attribute,
)
from database.repositories.notifications import (
    create_notification as _create_notification,
    delete_notification as _delete_notification,
    get_notification_by_id as _get_notification_by_id,
    list_user_notifications as _list_user_notifications,
    update_notification_attribute as _update_notification_attribute,
)
from database.repositories.profiles import get_active_profile_by_id, get_profile_by_id, list_user_profiles

logger = logging.getLogger(__name__)


#Get user/profile data operations
async def orm_get_user(session: AsyncSession, chat_id: int):
    result = await session.execute(
        select(User).where(User.telegram_id == chat_id, User.deleted_at.is_(None))
    )
    user = result.scalars().first()
    return user

async def orm_get_user_by_login(session: AsyncSession, login: str):
    result = await session.execute(
        select(User).where(User.login == login, User.deleted_at.is_(None))
    )
    user = result.scalars().first()
    return user

async def orm_get_current_profile_data(session: AsyncSession, chat_id: int):
    user = await orm_get_user(session, chat_id)
    if (not user) or (user.current_profile == None) :
        return None
    search_profile = await session.execute(
        select(Profile).where(
            Profile.id == user.current_profile,
            Profile.deleted_at.is_(None),
        )
    )
    profile = search_profile.scalars().first()
    if not profile:
        return None
    return profile

async def orm_get_profile_by_id(session: AsyncSession, profile_id: int):
    return await get_active_profile_by_id(session, profile_id)

async def orm_get_trusted_profiles_list(session: AsyncSession, chat_id: int):
    query = (
            select(Profile)
            .join(TrustedPersonProfiles, Profile.id == TrustedPersonProfiles.profile_id)
            .join(User, TrustedPersonProfiles.trusted_person_user_id == User.id)
            .where(User.telegram_id == chat_id, Profile.deleted_at.is_(None))
        )
    profiles_result = await session.execute(query)
    profiles = [profile.to_dict() for profile in profiles_result.scalars().all()]
    return profiles

async def orm_get_user_own_profiles_list(session: AsyncSession, chat_id: int):
    return await list_user_profiles(session, chat_id)

#Get seizures data
async def orm_get_seizures_by_profile_ascending(session: AsyncSession, current_profile_id: int):
    query = (
            select(Seizure)
            .where(Seizure.profile_id == int(current_profile_id))
            .order_by(asc(Seizure.date))
        )
    seizures_result = await session.execute(query)
    return seizures_result.scalars().all()

async def orm_get_seizures_by_profile_descending(session: AsyncSession, current_profile_id: int):
    query = (
            select(Seizure)
            .where(Seizure.profile_id == int(current_profile_id))
            .order_by(desc(Seizure.date))
        )
    seizures_result = await session.execute(query)
    return seizures_result.scalars().all()

async def orm_get_average_duration(session: AsyncSession, current_profile_id: int):
    query = (
        select(func.avg(Seizure.duration))
        .where(
            Seizure.profile_id == int(current_profile_id),
            Seizure.duration.is_not(None)
        )
    )
    result = await session.execute(query)
    avg_duration = result.scalar()
    return avg_duration

async def orm_get_seizures_with_duration(session: AsyncSession, current_profile_id: int):
    query = (
        select(Seizure)
        .where(
            (Seizure.profile_id == int(current_profile_id)),
            (Seizure.duration.is_not(None))
        )
    )
    seizure_with_duration = await session.execute(query)
    return seizure_with_duration.scalars().all()

async def orm_get_seizure_info(session: AsyncSession, seizure_id: int, current_profile_id: int):
    query = (
        select(Seizure)
        .filter(
            (Seizure.profile_id == int(current_profile_id)),
            (Seizure.id == int(seizure_id))
        )
    )
    seizures_res = await session.execute(query)
    return seizures_res.scalars().first()

async def orm_get_seizures_for_a_specific_period(session: AsyncSession,  curr_prof: int, year: int, month: int = 1, day: int = 1):
    date = datetime(year=year, month=month, day=day)
    query = (
        select(Seizure)
        .where(
            (cast(Seizure.date, Date) >= date),
            (Seizure.profile_id == int(curr_prof))
        )
    )
    result = await session.execute(query)
    records = result.scalars().all()
    return records

async def orm_get_seizures_for_a_specific_year(
    session: AsyncSession,
    curr_prof: int,
    year: int
):
    start_date = date(year, 1, 1)
    end_date = date(year + 1, 1, 1)

    query = (
        select(Seizure)
        .where(
            Seizure.profile_id == curr_prof,
            cast(Seizure.date, Date) >= start_date,
            cast(Seizure.date, Date) < end_date
        )
    )
    result = await session.execute(query)
    return result.scalars().all()

async def orm_delete_seizure(session: AsyncSession, seizure_id: int, current_profile_id: int) -> bool:
    from database.repositories.seizures import delete_seizure

    return await delete_seizure(session, seizure_id, current_profile_id)

#TRUSTED PERSON FUNCS
async def orm_get_can_trusted_person_read(
        session: AsyncSession,
        trusted_person_id: int,
        profile_owner_id: int,
        profile_id: int
    ) -> bool:
    query = (
        select(TrustedPersonProfiles)
        .where(
            (TrustedPersonProfiles.trusted_person_user_id == int(trusted_person_id))
            & (TrustedPersonProfiles.profile_owner_id == int(profile_owner_id))
            & (TrustedPersonProfiles.profile_id == int(profile_id))
        )
    )
    result = await session.execute(query)
    tr_person = result.scalars().first()
    return bool(tr_person and tr_person.can_read)

async def orm_delete_tursted_person(session: AsyncSession, tpp_id: int):
    query = (
        delete(TrustedPersonProfiles)
        .where(
            TrustedPersonProfiles.id == int(tpp_id)
        )
    )
    del_res = await session.execute(query)
    deleted_count = del_res.rowcount
    return deleted_count > 0

async def orm_get_can_trusted_person_edit(
        session: AsyncSession,
        trusted_person_id: int,
        profile_owner_id: int,
        profile_id: int
    ) -> bool:
    query = (
        select(TrustedPersonProfiles)
        .where(
            (TrustedPersonProfiles.trusted_person_user_id == int(trusted_person_id))
            & (TrustedPersonProfiles.profile_owner_id == int(profile_owner_id))
            & (TrustedPersonProfiles.profile_id == int(profile_id))
        )
    )
    result = await session.execute(query)
    tr_person = result.scalars().first()
    return bool(tr_person and tr_person.can_edit)

async def orm_switch_trusted_profile_notify_edit_state(
        session: AsyncSession,
        tpp_id: int,
        getting_notify: bool = False,
        switch_edit: bool = False,
    ):
    query = (
        select(TrustedPersonProfiles)
        .where(
            TrustedPersonProfiles.id == int(tpp_id)
        )
    )
    if switch_edit:
        result = await session.execute(query)
        tr_person = result.scalars().first()
        if tr_person is None:
            return None

        if tr_person.can_edit:
            tr_person.can_edit = False
        elif not tr_person.can_edit:
            tr_person.can_edit = True
        return tr_person
    if getting_notify:
        result = await session.execute(query)
        tr_person = result.scalars().first()
        if tr_person is None:
            return None

        if tr_person.get_notification:
            tr_person.get_notification = False
        elif not tr_person.get_notification:
            tr_person.get_notification = True
        return tr_person

async def orm_update_list_of_trusted_profiles(session: AsyncSession, chat_id: int):
    query = (
            select(Profile)
            .join(TrustedPersonProfiles, Profile.id == TrustedPersonProfiles.profile_id)
            .join(User, TrustedPersonProfiles.trusted_person_user_id == User.id)
            .where(User.telegram_id == chat_id)
        )
    profiles_result = await session.execute(query)
    profiles = [profile.to_dict() for profile in profiles_result.scalars().all()]
    return profiles

async def orm_get_trusted_users_with_full_info(session: AsyncSession, chat_id: int):
    owner_alias = aliased(User)
    query = (
        select(User, TrustedPersonProfiles, Profile, owner_alias)
        .join(TrustedPersonProfiles, User.id == TrustedPersonProfiles.trusted_person_user_id)
        .join(owner_alias, TrustedPersonProfiles.profile_owner_id == owner_alias.id)
        .join(Profile, TrustedPersonProfiles.profile_id == Profile.id)
        .where(owner_alias.telegram_id == chat_id)
    )
    result = await session.execute(query)
    trusted_data = []
    for trusted_user, trusted_profile, profile, owner in result.all():
        trusted_data.append({
            'trusted_user': trusted_user.to_dict(),
            'profile_owner': owner.to_dict(),
            'profile': profile.to_dict(),
            'permissions': {
                'id': trusted_profile.id,
                'can_read': trusted_profile.can_read,
                'can_edit': trusted_profile.can_edit,
                'created_at': trusted_profile.created_at,
                'get_notification': trusted_profile.get_notification
            }
        })

    return trusted_data

async def orm_create_profile(
        session: AsyncSession,
        user_id,
        profile_name,
        type_of_epilepsy,
        age,
        sex,
        created_at
    ):
    new_profile = Profile(
            user_id=user_id,
            profile_name=profile_name,
            type_of_epilepsy=type_of_epilepsy,
            age=age,
            sex=sex,
            created_at=created_at
        )
    session.add(new_profile)

async def orm_set_current_profile(session: AsyncSession, user_id: int, profile_id: int):
    from database.repositories.profiles import set_user_current_profile

    await set_user_current_profile(session, user_id, profile_id)

async def get_top_seizure_features(session: AsyncSession, profile_id: int) -> dict:
    symptom_query = (
        select(Symptom.symptom_name, func.count(Symptom.id))
        .join(SeizureSymptom, Symptom.id == SeizureSymptom.symptom_id)
        .join(Seizure, Seizure.id == SeizureSymptom.seizure_id)
        .where(Symptom.profile_id == profile_id)
        .group_by(Symptom.symptom_name)
        .order_by(desc(func.count(Symptom.id)))
        .limit(5)
    )
    symptoms_result = await session.execute(symptom_query)
    top_symptoms = [{"name": name, "count": count} for name, count in symptoms_result.all()]
    trigger_query = (
        select(Trigger.trigger_name, func.count(Trigger.id))
        .join(SeizureTrigger, Trigger.id == SeizureTrigger.trigger_id)
        .join(Seizure, Seizure.id == SeizureTrigger.seizure_id)
        .where(Trigger.profile_id == profile_id)
        .group_by(Trigger.trigger_name)
        .order_by(desc(func.count(Trigger.id)))
        .limit(5)
    )
    triggers_result = await session.execute(trigger_query)
    top_triggers = [{"name": name, "count": count} for name, count in triggers_result.all()]
    type_query = (
        select(Seizure.type_of_seizure, func.count(Seizure.id))
        .where(Seizure.profile_id == profile_id)
        .where(Seizure.type_of_seizure.isnot(None))
        .group_by(Seizure.type_of_seizure)
        .order_by(desc(func.count(Seizure.id)))
        .limit(5)
    )
    types_result = await session.execute(type_query)
    top_types = [{"name": name, "count": count} for name, count in types_result.all()]
    return {
        "top_symptoms": top_symptoms,
        "top_triggers": top_triggers,
        "top_types": top_types
    }

async def get_avg_duration_by_month(session: AsyncSession, profile_id: int, year: int):
    query = (
        select(
            extract('month', func.to_date(Seizure.date, 'YYYY-MM-DD')).label("month"),
            func.avg(Seizure.duration).label("avg_duration")
        )
        .where(
            Seizure.profile_id == profile_id,
            func.extract('year', func.to_date(Seizure.date, 'YYYY-MM-DD')) == year,
            Seizure.duration.isnot(None)
        )
        .group_by("month")
        .order_by("month")
    )
    result = await session.execute(query)
    return result.all()  # [(1, 24.3), (2, 18.9), ...]

async def orm_update_seizure(session: AsyncSession, seizure_id: int, current_profile_id: int, attribute: str, new_value):
    from database.repositories.seizures import update_seizure_attribute

    return await update_seizure_attribute(
        session, seizure_id, current_profile_id, attribute, new_value
    )

#PROFILE
async def orm_get_profile_info(session: AsyncSession, profile_id: int) -> bool:
    return await get_active_profile_by_id(session, profile_id)

async def orm_update_profile_settings(session: AsyncSession, profile_id: int, attribute: str, new_value):
    from database.repositories.profiles import update_profile_attribute

    return await update_profile_attribute(session, profile_id, attribute, new_value)

async def orm_delete_profile(session: AsyncSession, profile_id: int):
    from database.repositories.profiles import delete_profile_by_id

    return await delete_profile_by_id(session, profile_id)

#MEDICATIONS
async def orm_get_profile_medications_list(session: AsyncSession, current_profile_id: int):
    courses = await _list_profile_medications(session, current_profile_id)
    if not courses:
        return None
    return courses


async def orm_delete_profile_medication(session: AsyncSession, current_profile_id: int, medication_id: int):
    return await _delete_medication(session, current_profile_id, medication_id)


async def orm_get_profile_medication_by_id(session: AsyncSession, current_profile_id: int, medication_id: int):
    return await _get_medication_by_id(session, current_profile_id, medication_id)


async def orm_update_medication_attribute(
    session: AsyncSession,
    current_profile_id: int,
    medication_id: int,
    attribute: str,
    new_value,
):
    return await _update_medication_attribute(
        session, current_profile_id, medication_id, attribute, new_value
    )


async def orm_create_medication_course(session: AsyncSession, *args):
    await _create_medication_course(
        session,
        profile_id=args[0],
        medication_name=args[1],
        dosage=args[2],
        frequency=args[3],
        notes=args[4],
        start_date=args[5],
        end_date=args[6],
    )

#NOTIFICATIONS
async def orm_create_new_notification(session: AsyncSession, *args):
    await _create_notification(
        session,
        user_id=int(args[0]),
        notify_time=args[1],
        note=args[2],
        pattern=args[3],
    )


async def orm_get_all_user_notifications(session: AsyncSession, user_id_db: int):
    notifications = await _list_user_notifications(session, user_id_db)
    if not notifications:
        return None
    return notifications


async def orm_get_notification_by_id(session: AsyncSession, user_id_db: int, notification_id: int):
    return await _get_notification_by_id(session, user_id_db, notification_id)


async def orm_update_notification_settings(
    session: AsyncSession,
    user_id_db: int,
    notification_id: int,
    attribute: str,
    new_value,
):
    return await _update_notification_attribute(
        session, user_id_db, notification_id, attribute, new_value
    )


async def orm_delete_notification(session: AsyncSession, user_id_db: int, notification_id: int):
    return await _delete_notification(session, user_id_db, notification_id)

#SYMPTOMS AND TRIGGERS
async def orm_get_global_symptoms(session: AsyncSession):
    global_symptoms = await session.execute(
        select(Symptom.symptom_name)
        .where(Symptom.profile_id.is_(None))
    )
    global_symptoms = [symptom.symptom_name for symptom in global_symptoms.all()]
    return global_symptoms

async def orm_get_global_triggers(session: AsyncSession):
    try:
        result = await session.execute(
            select(Trigger.trigger_name)
            .where(Trigger.profile_id.is_(None))
        )
        global_triggers = [row.trigger_name for row in result.fetchall()]
        return global_triggers
    except Exception:
        logger.exception("Failed to load global triggers")
        return []

async def orm_get_symptoms_by_profile(session: AsyncSession, profile_id: int):
    profile_symptoms = await session.execute(
        select(Symptom.symptom_name)
        .where(Symptom.profile_id == profile_id)
    )
    profile_symptoms = [symptom.symptom_name for symptom in profile_symptoms.all()]
    return profile_symptoms if profile_symptoms else None

async def orm_get_triggers_by_profile(session: AsyncSession, profile_id: int) -> list[str]:
    try:
        result = await session.execute(
            select(Trigger.trigger_name)
            .where(Trigger.profile_id == int(profile_id))
        )
        profile_triggers = [row.trigger_name.capitalize() for row in result.fetchall()]
        return profile_triggers
    except Exception:
        logger.exception("Failed to load profile triggers")
        return []
