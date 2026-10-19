from handlers_logic.seizure_form.skip import handle_skip_step
from handlers_logic.states_factories import SeizureForm
from i18n import t


class MemoryState:
    def __init__(self, current: str | None):
        self.current = current
        self.storage: dict = {}

    async def get_state(self):
        return self.current

    async def set_state(self, value):
        self.current = value.state if hasattr(value, "state") else value

    async def get_data(self):
        return self.storage

    async def update_data(self, **kwargs):
        self.storage.update(kwargs)


async def test_skip_from_hour_describes_duration_screen():
    state = MemoryState("SeizureForm:hour")
    form_turn = await handle_skip_step(state, db=None, chat_id=1, profile_id=None)
    assert form_turn.ack is True
    assert form_turn.screens[0].edit is True
    assert form_turn.screens[0].text == t("seizure_form.select_duration")
    assert state.current == SeizureForm.duration.state


async def test_skip_outside_form_asks_to_restart():
    state = MemoryState(None)
    form_turn = await handle_skip_step(state, db=None, chat_id=1, profile_id=None)
    assert form_turn.screens[0].edit is False
    assert form_turn.screens[0].text == t("seizure_form.restart")
