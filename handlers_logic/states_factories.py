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
    #minutes_range = State()
    severity = State()
    duration = State()
    comment = State()
    symptoms = State()
    video_tg_id = State()
    location = State()
    medication = State()