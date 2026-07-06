from services import cache_keys


def test_invalidation_contract_documents_seizure_create() -> None:
    groups = cache_keys.INVALIDATION_CONTRACT["seizure.create"]
    assert "profile_triggers" in groups
    assert "global_symptoms" in groups


def test_invalidation_contract_documents_trusted_person_mutations() -> None:
    groups = cache_keys.INVALIDATION_CONTRACT["trusted_person.mutate"]
    assert "trusted_persons" in groups
    assert "profiles_list:trusted" in groups
