from services.profile_ref import format_profile_key, parse_profile_ref


def test_parse_profile_ref_round_trip() -> None:
    raw = format_profile_key(12, "Основной")
    parsed = parse_profile_ref(raw)
    assert parsed is not None
    assert parsed.id == 12
    assert parsed.name == "Основной"


def test_parse_profile_ref_keeps_pipe_inside_name() -> None:
    parsed = parse_profile_ref("7|A|B")
    assert parsed is not None
    assert parsed.id == 7
    assert parsed.name == "A|B"


def test_parse_profile_ref_rejects_malformed_values() -> None:
    assert parse_profile_ref(None) is None
    assert parse_profile_ref("") is None
    assert parse_profile_ref("Основной") is None
    assert parse_profile_ref("|name") is None
    assert parse_profile_ref("12|") is None
