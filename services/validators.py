import re

check_name_pattern = r'^[A-Za-zА-Яа-я]{1,20}$'
check_login_pattern = r'^[A-Za-zА-Яа-я0-9._-]{6,25}$'


def validate_name_of_user_form(user_name: str) ->  bool:
    return bool(re.fullmatch(check_name_pattern, user_name))

def validate_login_of_user_form(user_name: str) ->  bool:
    return bool(re.fullmatch(check_login_pattern, user_name))
