"""Backward-compatible re-exports. Prefer i18n.t() and locale YAML files."""

from i18n import get_epilepsy_symptoms, get_epilepsy_triggers, get_seizure_types, t


class _LexiconMapping:
    _KEY_MAP = {
        "welcome": "start.welcome",
        "to_register": "start.to_register",
        "policy": "start.policy",
        "cancel_script": "common.cancel_script",
        "not_in_script": "common.not_in_script",
        "enter_username": "user.enter_username",
        "enter_login": "user.enter_login",
        "incorrect_login": "user.incorrect_login",
        "user_exist": "user.user_exist",
        "login_exist": "user.login_exist",
        "yes": "common.yes",
        "no": "common.no",
        "offer_to_create_profile": "user.offer_to_create_profile",
        "info_about_profile": "profile.info_about_profile",
        "enter_profile_name": "profile.enter_profile_name",
        "incorrect_profile_name": "profile.incorrect_profile_name",
        "enter_type_of_epilepsy": "profile.enter_type_of_epilepsy",
        "enter_drugs_info": "profile.enter_drugs_info",
        "enter_drugs": "profile.enter_drugs",
        "incorrect_drugs": "profile.incorrect_drugs",
        "enter_age": "profile.enter_age",
        "incorrect_age": "profile.incorrect_age",
        "enter_sex": "profile.enter_sex",
        "timezone_info": "user.timezone_info",
        "enter_timezone": "user.enter_timezone",
        "sos_notify": "sos.notify_template",
    }

    def __getitem__(self, key: str) -> str:
        mapped = self._KEY_MAP.get(key, key)
        return t(mapped)


class _ButtonMapping:
    _KEY_MAP = {
        "focal_type": "buttons.focal_type",
        "generalized_type": "buttons.generalized_type",
        "combied_type": "buttons.combied_type",
        "unidentified_type": "buttons.unidentified_type",
        "male": "buttons.male",
        "female": "buttons.female",
        "send_geolocation": "buttons.send_geolocation",
        "submit": "buttons.submit",
        "cancel": "buttons.cancel",
    }

    def __getitem__(self, key: str) -> str:
        return t(self._KEY_MAP[key])


class _LazyList:
    def __iter__(self):
        return iter(get_epilepsy_triggers())

    def __getitem__(self, index: int) -> str:
        return get_epilepsy_triggers()[index]

    def __len__(self) -> int:
        return len(get_epilepsy_triggers())


class _LazySymptomList:
    def __iter__(self):
        return iter(get_epilepsy_symptoms())

    def __getitem__(self, index: int) -> str:
        return get_epilepsy_symptoms()[index]

    def __len__(self) -> int:
        return len(get_epilepsy_symptoms())


class _LazySeizureTypes:
    def items(self):
        return get_seizure_types().items()

    def __getitem__(self, key: int) -> str:
        return get_seizure_types()[int(key)]

    def __iter__(self):
        return iter(get_seizure_types())


LEXICON_RU = _LexiconMapping()
LEXICON_BUTTONS = _ButtonMapping()
LEXICON_EPILEPSY_TRIGGERS = _LazyList()
LEXICON_EPILEPSY_SYMPTOMS = _LazySymptomList()
LEXICON_TYPES_OF_SEIZURE = _LazySeizureTypes()
LEXICON_COMMANDS: dict[str, str] = {}
