from services.profile_ref import ProfileRef


def profile_ref_for_viewer(
    viewer_id: int,
    owner_id: int,
    profile_id: int,
    profile_name: str,
    *,
    link_can_read: bool | None,
    link_can_edit: bool | None,
) -> ProfileRef | None:
    if viewer_id == owner_id:
        return ProfileRef(id=profile_id, name=profile_name, can_edit=True, is_owner=True)
    if not link_can_read:
        return None
    return ProfileRef(
        id=profile_id,
        name=profile_name,
        can_edit=bool(link_can_edit),
        is_owner=False,
    )
