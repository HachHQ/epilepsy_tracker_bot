import database.orm_query as orm_query


def test_legacy_seizure_write_helpers_removed() -> None:
    assert not hasattr(orm_query, "orm_add_new_seizure")
    assert not hasattr(orm_query, "create_seizure")


def test_get_seizures_with_details_removed_as_unused_duplicate() -> None:
    assert not hasattr(orm_query, "get_seizures_with_details")


def test_active_orm_helpers_still_available() -> None:
    for name in (
        "orm_get_seizures_by_profile_descending",
        "orm_delete_seizure",
        "orm_update_seizure",
        "get_top_seizure_features",
    ):
        assert hasattr(orm_query, name), name
