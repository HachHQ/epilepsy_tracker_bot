import math
from sqlalchemy import select, update, delete, asc, desc, cast, Date, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, aliased, selectinload
from datetime import datetime

from database.models import (User, Profile, RequestStatus, TrustedPersonProfiles,
                              TrustedPersonRequest, Seizure, SeizureSymptom, SeizureTrigger, Symptom, Trigger)

#Get user/profile data operations
async def orm_get_user(session: AsyncSession, chat_id: int):
    result = await session.execute(select(User).filter(User.telegram_id == chat_id))
    user = result.scalars().first()
    return user

async def orm_get_user_by_login(session: AsyncSession, login: str):
    result = await session.execute(select(User).filter(User.login == login))
    user = result.scalars().first()
    return user

async def orm_get_current_profile_data(session: AsyncSession, chat_id: int):
    user = await orm_get_user(session, chat_id)
    if (not user) or (user.current_profile == None) :
        return None
    search_profile = await session.execute(select(Profile).filter(Profile.id == user.current_profile))
    profile = search_profile.scalars().first()
    if not profile:
        return None
    return profile

async def orm_get_profile_by_id(session: AsyncSession, profile_id: int):
    search_profile = await session.execute(select(Profile).filter(Profile.id == int(profile_id)))
    profile = search_profile.scalars().first()
    return profile

async def orm_get_trusted_profiles_list(session: AsyncSession, chat_id: int):
    query = (
            select(Profile)
            .join(TrustedPersonProfiles, Profile.id == TrustedPersonProfiles.profile_id)
            .join(User, TrustedPersonProfiles.trusted_person_user_id == User.id)
            .where(User.telegram_id == chat_id)
        )
    profiles_result = await session.execute(query)
    profiles = [profile.to_dict() for profile in profiles_result.scalars().all()]
    return profiles

async def orm_get_user_own_profiles_list(session: AsyncSession, chat_id: int):
    query = (
            select(Profile)
            .join(User)
            .where(User.telegram_id == chat_id)
        )
    profiles_result = await session.execute(query)
    profiles = [profile.to_dict() for profile in profiles_result.scalars().all()]
    return profiles


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

async def get_seizures_with_details(session: AsyncSession, profile_id: int):
    result = await session.execute(
        select(Seizure)
        .where(Seizure.profile_id == profile_id)
        .options(
            selectinload(Seizure.symptoms).joinedload(SeizureSymptom.symptom),
            selectinload(Seizure.triggers).joinedload(SeizureTrigger.trigger)
        )
    )
    seizures = result.scalars().all()

    seizure_data = []
    for seizure in seizures:
        symptoms = [ss.symptom.symptom_name for ss in seizure.symptoms if ss.symptom]
        triggers = [st.trigger.trigger_name for st in seizure.triggers if st.trigger]

        seizure_data.append({
            "id": seizure.id,
            "date": seizure.date,
            "time": seizure.time,
            "severity": seizure.severity,
            "duration": seizure.duration,
            "comment": seizure.comment,
            "count": seizure.count,
            "type_of_seizure": seizure.type_of_seizure,
            "location": seizure.location,
            "video_tg_id": seizure.video_tg_id,
            "created_at": seizure.created_at,
            "updated_at": seizure.updated_at,
            "symptoms": symptoms,
            "triggers": triggers,
        })

    return seizure_data

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

async def orm_delete_seizure(session: AsyncSession, seizure_id: int, current_profile_id: int) -> bool:
    query = (
        delete(Seizure)
        .where((Seizure.id == int(seizure_id)) & (Seizure.profile_id == int(current_profile_id)))
    )
    del_res = await session.execute(query)
    deleted_count = del_res.rowcount
    return deleted_count > 0

async def orm_get_profile_info(session: AsyncSession, profile_id: int) -> bool:
    query = (
        select(Profile)
        .where(Profile.id == int(profile_id))
    )
    res = await session.execute(query)
    profile = res.scalars().first()
    return profile if profile is not None else None

#Trusted person operations
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
            (TrustedPersonProfiles.profile_owner_id == int(profile_owner_id))
            (TrustedPersonProfiles.profile_id == int(profile_id))
        )
    )
    result = await session.execute(query)
    tr_person = result.scalars().first()
    return tr_person.can_read

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
            (TrustedPersonProfiles.profile_owner_id == int(profile_owner_id))
            (TrustedPersonProfiles.profile_id == int(profile_id))
        )
    )
    result = await session.execute(query)
    tr_person = result.scalars().first()
    return tr_person.can_edit

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
                #'can_read': trusted_profile.can_read,
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
    query = (
        select(User)
        .where(
            (User.telegram_id == int(user_id))
        )
    )
    res = await session.execute(query)
    user = res.scalars().first()
    user.current_profile = int(profile_id)

async def get_seizures_with_details(session: AsyncSession, profile_id: int):
    result = await session.execute(
        select(Seizure)
        .where(Seizure.profile_id == profile_id)
        .options(
            selectinload(Seizure.symptoms).joinedload(SeizureSymptom.symptom),
            selectinload(Seizure.triggers).joinedload(SeizureTrigger.trigger)
        )
    )
    seizures = result.scalars().all()

    seizure_data = []
    for seizure in seizures:
        symptoms = [ss.symptom.symptom_name for ss in seizure.symptoms if ss.symptom]
        triggers = [st.trigger.trigger_name for st in seizure.triggers if st.trigger]

        seizure_data.append({
            "id": seizure.id,
            "date": seizure.date,
            "time": seizure.time,
            "severity": seizure.severity,
            "duration": seizure.duration,
            "comment": seizure.comment,
            "count": seizure.count,
            "type_of_seizure": seizure.type_of_seizure,
            "location": seizure.location,
            "video_tg_id": seizure.video_tg_id,
            "created_at": seizure.created_at,
            "updated_at": seizure.updated_at,
            "symptoms": symptoms,
            "triggers": triggers,
        })

    return seizure_data

async def create_seizure(
        session: AsyncSession,
        profile_id,
        date,
        time,
        severity,
        duration,
        comment,
        count,
        video_tg_id,
        trigger_names,
        symptom_names,
        location,
        creator_login
    ):
    new_seizure = Seizure(
        profile_id = profile_id,
        date = date,
        time = time if time else None,
        severity = severity if severity else None,
        duration = int(duration) if duration else None,
        comment = comment if comment else None,
        count = int(count) if count else None,
        video_tg_id = video_tg_id if video_tg_id else None,
        location = location if location else None,
        creator_login = creator_login
    )
    session.add(new_seizure)
    await session.flush()
    symptom_ids = []
    if symptom_names is not None:
        for name in symptom_names:
            symptom = await session.scalar(
                select(Symptom).where(
                    Symptom.symptom_name == name,
                    (Symptom.profile_id == None) | (Symptom.profile_id == profile_id)
                )
            )
            if not symptom:
                symptom = Symptom(symptom_name=name, profile_id=profile_id)
                session.add(symptom)
                await session.flush()
            symptom_ids.append(symptom.id)
    trigger_ids = []
    if trigger_names is not None:
        for name in trigger_names:
            trigger = await session.scalar(
                select(Trigger).where(
                    Trigger.trigger_name == name,
                    (Trigger.profile_id == None) | (Trigger.profile_id == profile_id)
                )
            )
            if not trigger:
                trigger = Trigger(trigger_name=name.lower().capitalize(), profile_id=profile_id)
                session.add(trigger)
                await session.flush()
            trigger_ids.append(trigger.id)
    if len(symptom_ids) > 0:
        for sid in symptom_ids:
            session.add(SeizureSymptom(seizure_id=new_seizure.id, symptom_id=sid))
    if len(trigger_ids) > 0:
        for tid in trigger_ids:
            session.add(SeizureTrigger(seizure_id=new_seizure.id, trigger_id=tid))


async def orm_add_new_seizure(
        session: AsyncSession,
        profile_id,
        date,
        time,
        severity,
        duration,
        comment,
        count,
        video_tg_id,
        triggers,
        location,
        symptoms,
        creator_login
    ):
    new_seizure = Seizure(
        profile_id = profile_id,
        date = date,
        time = time if time else None,
        severity = severity if severity else None,
        duration = int(duration) if duration else None,
        comment = comment if comment else None,
        count = int(count) if count else None,
        video_tg_id = video_tg_id if video_tg_id else None,
        triggers = triggers if triggers else None,
        location = location if location else None,
        symptoms = symptoms if symptoms else None,
        creator_login = creator_login
    )
    session.add(new_seizure)

async def orm_update_seizure(session: AsyncSession, seizure_id: int, current_profile_id: int, attribute: str, new_value):
    query = (
        select(Seizure)
        .filter(
            (Seizure.profile_id == int(current_profile_id)),
            (Seizure.id == int(seizure_id))
        )
    )
    res = await session.execute(query)
    sz = res.scalars().first()
    if not sz:
        return None

    if hasattr(sz, attribute):
        setattr(sz, attribute, new_value)
    else:
        raise ValueError(f"Атрибут '{attribute}' не существует в модели Seizure.")
    return sz


#GET SYMPTOMS AND TRIGGERS FROM DB
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
    except Exception as e:
        print(f"Database error: {e}")
        return []

async def orm_get_symptoms_by_profile(session: AsyncSession, profile_id: int):
    profile_symptoms = await session.execute(
        select(Symptom.name)
        .where(Symptom.profile_id == profile_id)
    )
    profile_symptoms = [symptom.symptom_name for symptom in profile_symptoms.all()]
    return profile_symptoms if profile_symptoms else None
async def orm_get_triggers_by_profile(session: AsyncSession, profile_id: int):
    result = await session.execute(
        select(Trigger.name)
        .where(Trigger.profile_id == profile_id)
    )
    rows = result.fetchall()
    if not rows:
        print("No triggers found")
        return None
    profile_triggers = [trigger.trigger_name for trigger in result.fetchall()]
    print(profile_triggers)
    return profile_triggers if profile_triggers else None