import re

check_name_pattern = r'^[A-Za-zА-Яа-я]{1,25}$'
check_profile_name_pattern = r'^[A-Za-zА-Яа-я]{1,40}$'
check_login_pattern = r'^[A-Za-zА-Яа-я0-9._-]{6,25}$'
check_age_pattern = r"^(?:[1-9]|[1-9][0-9]|1[0-2][0-9]|130)$"
check_drugs_pattern = r"^[a-zA-Zа-яА-ЯёЁ0-9,\.\s]+$"

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
