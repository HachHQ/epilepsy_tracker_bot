from aiogram.fsm.state import StatesGroup, State

class UserForm(StatesGroup):
    name = State()
    login = State()
    timezone = State()
    code_word = State()

class ProfileForm(StatesGroup):
    profile_name = State()
    type_of_epilepsy = State()
    biological_species = State()
    age = State()
    sex = State()
    check_form = State()

class TrustedPersonForm(StatesGroup):
    trusted_person_login = State()
    correct_trusted_person_login = State()
    selected_profile = State()
    confirm_transfer = State()

class MedicationCourse(StatesGroup):
    medication_name = State()
    dosage = State()
    frequency = State()
    notes = State()
    start_date = State()
    end_date = State()

class SeizureForm(StatesGroup):
    date = State()
    year = State()
    month = State()
    day = State()
    hour = State()
    duration = State()
    count = State()
    triggers = State()
    type_of_seizure = State()
    severity = State()
    comment = State()
    #symptoms = State()
    video_tg_id = State()
    location = State()
    #medication = State()
    states_sequence = [
        date, year, month, day, hour, duration, count, type_of_seizure, triggers,
        #type_of_seizure,
        severity, comment,
        #symptoms,
        video_tg_id, location#, medication
    ]
    @classmethod
    def next_state(cls, current_state: str | None) -> State | None:
        if not current_state:
            return cls.states_sequence[0]

        for idx, state in enumerate(cls.states_sequence):
            if state.state == current_state:
                return cls.states_sequence[idx + 1] if idx + 1 < len(cls.states_sequence) else None
        return None

class NotificationForm(StatesGroup):
    notify_time = State()
    note = State()
    pattern = State()

class SosForm(StatesGroup):
    geolocation = State()

class GetExcelTableForm(StatesGroup):
    get_xlsx_file = State()