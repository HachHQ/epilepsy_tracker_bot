from dataclasses import dataclass


@dataclass(frozen=True)
class ProfileRef:
    id: int
    name: str
    can_edit: bool = True
    is_owner: bool = True


def format_profile_key(profile_id: int, name: str) -> str:
    return f"{profile_id}|{name}"


def parse_profile_ref(raw: str | None) -> ProfileRef | None:
    if not raw or "|" not in raw:
        return None
    raw_id, name = raw.split("|", 1)
    if not raw_id.isdigit() or not name:
        return None
    return ProfileRef(id=int(raw_id), name=name)
