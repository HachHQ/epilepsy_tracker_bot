from config_data.pagination import (
    JOURNAL_NOTES_PER_PAGE,
    MEDICATIONS_PER_PAGE,
    NOTIFICATIONS_PER_PAGE,
    TRUSTED_PERSONS_PER_PAGE,
)


def test_pagination_constants_are_positive() -> None:
    for value in (
        JOURNAL_NOTES_PER_PAGE,
        NOTIFICATIONS_PER_PAGE,
        MEDICATIONS_PER_PAGE,
        TRUSTED_PERSONS_PER_PAGE,
    ):
        assert value > 0


def test_pagination_constants_match_domain_defaults() -> None:
    assert JOURNAL_NOTES_PER_PAGE == 8
    assert NOTIFICATIONS_PER_PAGE == 6
    assert MEDICATIONS_PER_PAGE == 5
    assert TRUSTED_PERSONS_PER_PAGE == 3
