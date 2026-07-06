from aiogram.utils.keyboard import InlineKeyboardBuilder

from i18n import t


def get_medication_sumbenu():
    builder = InlineKeyboardBuilder()
    builder.button(text=t("buttons.add_medication"), callback_data="add_medication")
    builder.button(text=t("buttons.manage"), callback_data="medication_settings")
    builder.button(text=t("common.back"), callback_data="to_menu_edit")
    builder.adjust(1)
    return builder.as_markup()


def get_skip_cancel_buttons():
    builder = InlineKeyboardBuilder()
    builder.button(text=t("buttons.cancel_action"), callback_data='cancel_fsm_script')
    builder.button(text=t("buttons.skip_step"), callback_data="skip_note_for_medication")
    builder.adjust(1)
    return builder.as_markup()


def get_actual_med_cancel_buttons():
    builder = InlineKeyboardBuilder()
    builder.button(text=t("buttons.cancel_action"), callback_data='cancel_fsm_script')
    builder.button(text=t("buttons.still_taking"), callback_data="skip_end_date_for_medication")
    builder.adjust(1)
    return builder.as_markup()


def get_deleting_medication_kb(mdc_id, prof_id):
    builder = InlineKeyboardBuilder()
    builder.button(text=t("common.yes"), callback_data=f'delete_med_prof:yes:{mdc_id}:{prof_id}')
    builder.button(text=t("common.no"), callback_data=f"delete_med_prof:no:{mdc_id}:{prof_id}")
    builder.adjust(1)
    return builder.as_markup()
