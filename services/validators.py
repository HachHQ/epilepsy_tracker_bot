import re
from datetime import datetime

check_name_pattern = r'^[A-Za-zА-Яа-я]{1,25}$'
check_profile_name_pattern = r'^[A-Za-zА-Яа-я]{1,40}$'
check_login_pattern = r'^[A-Za-zА-Яа-я0-9._-]{6,25}$'
check_age_pattern = r"^(?:[1-9]|[1-9][0-9]|1[0-2][0-9]|130)$"
check_drugs_pattern = r"^[a-zA-Zа-яА-ЯёЁ0-9\s][a-zA-Zа-яА-ЯёЁ0-9,\.\s]*[a-zA-Zа-яА-ЯёЁ0-9\s]$"
check_date = r"^(?P<year>\d{4})-(?P<month>0[1-9]|1[0-2])-(?P<day>0[1-9]|[12][0-9]|3[01])$"


def validate_name_of_user_form(user_name: str) ->  bool:
    return bool(re.fullmatch(check_name_pattern, user_name))

def validate_login_of_user_form(user_login: str) ->  bool:
    return bool(re.fullmatch(check_login_pattern, user_login))

def validate_name_of_profile_form(user_name: str) ->  bool:
    return bool(re.fullmatch(check_profile_name_pattern, user_name))

def validate_age_of_profile_form(age: str) -> bool:
    return bool(re.match(check_age_pattern, age))

def validate_list_of_drugs_of_profile_form(drugs: str) -> bool:
    return bool(re.match(check_drugs_pattern, drugs))

def validate_date(date_str: str) -> bool:
    date_pattern = re.compile(r"^(?P<year>\d{4})-(?P<month>0[1-9]|1[0-2])-(?P<day>0[1-9]|[12][0-9]|3[01])$")
    if not date_pattern.match(date_str):
        return False
    print('smthng')
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def validate_time(time: str) -> bool:
    time_pattern = re.compile(r"^(?P<hour>[01]?\d|2[0-3]):(?P<minute>[0-5]\d)$")
    if time_pattern.match(time):
        return True
    return False

def validate_count_of_seizures(count: str) -> bool:
    return count.isnumeric()

def validate_triggers_list(triggers: str) -> bool:
    return True if len(triggers) < 250 else False