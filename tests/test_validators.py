from services.validators import (
    validate_age_of_profile_form,
    validate_date,
    validate_login_of_user_form,
    validate_name_of_profile_form,
    validate_name_of_user_form,
    validate_time,
    validate_timezone,
)


def test_user_name_validation() -> None:
    assert validate_name_of_user_form("Артур")
    assert validate_name_of_user_form("Arthur")
    assert not validate_name_of_user_form("Arthur123")


def test_profile_name_validation() -> None:
    assert validate_name_of_profile_form("Пациент")
    assert not validate_name_of_profile_form("Пациент 1")


def test_login_validation() -> None:
    assert validate_login_of_user_form("arthur_01")
    assert not validate_login_of_user_form("short")


def test_age_validation() -> None:
    assert validate_age_of_profile_form("1")
    assert validate_age_of_profile_form("130")
    assert not validate_age_of_profile_form("131")


def test_date_and_time_validation() -> None:
    assert validate_date("2026-05-27")
    assert not validate_date("2026-02-31")
    assert validate_time("09:30")
    assert not validate_time("25:00")


def test_timezone_validation() -> None:
    assert validate_timezone("+7")
    assert validate_timezone("-3")
    assert not validate_timezone("7")
    assert not validate_timezone("+15")
