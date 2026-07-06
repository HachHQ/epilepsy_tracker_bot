from services import cache_keys


def test_invalidation_contract_documents_seizure_create() -> None:
    groups = cache_keys.INVALIDATION_CONTRACT["seizure.create"]
    assert groups == (
        "profile_triggers",
        "profile_symptoms",
        "global_triggers",
        "global_symptoms",
    )


def test_invalidation_contract_documents_seizure_partial_updates() -> None:
    assert cache_keys.INVALIDATION_CONTRACT["seizure.update.triggers"] == (
        "profile_triggers",
        "global_triggers",
    )
    assert cache_keys.INVALIDATION_CONTRACT["seizure.update.symptoms"] == (
        "profile_symptoms",
        "global_symptoms",
    )


def test_invalidation_contract_documents_trusted_person_mutations() -> None:
    groups = cache_keys.INVALIDATION_CONTRACT["trusted_person.mutate"]
    assert "trusted_persons" in groups
    assert "profiles_list:trusted" in groups
