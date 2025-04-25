from aiogram.fsm.state import StatesGroup, State

class UserForm(StatesGroup):
    name = State()
    login = State()
    check_form = State()

class ProfileForm(StatesGroup):
    profile_name = State()
    type_of_epilepsy = State()
    drugs = State()
    age = State()
    sex = State()
    timezone = State()
    check_form = State()

class TrustedPersonForm(StatesGroup):
    trusted_person_login = State()
    correct_trusted_person_login = State()
    selected_profile = State()
    confirm_transfer = State()

class UpdateSeizureAttribute(StatesGroup):
    choose_attribute = State()
    input_new_value = State()

class MedicationCourse(StatesGroup):
    name_of_medication = State()
    dose = State()
    reception_schedule = State()
    start_course = State()
    end_course = State()


class SeizureForm(StatesGroup):
    date = State()
    year = State()
    month = State()
    day = State()
    hour = State()
    count = State()
    triggers = State()
    type_of_seizure = State()

    severity = State()
    duration = State()
    comment = State()
    symptoms = State()
    video_tg_id = State()
    location = State()
    medication = State()
    states_sequence = [
        date, year, month, day, hour, count, triggers,
        type_of_seizure, severity, duration, comment,
        symptoms, video_tg_id, location, medication
    ]
    @classmethod
    def next_state(cls, current_state: str | None) -> State | None:
        if not current_state:
            return cls.states_sequence[0]

        for idx, state in enumerate(cls.states_sequence):
            if state.state == current_state:
                return cls.states_sequence[idx + 1] if idx + 1 < len(cls.states_sequence) else None
        return None