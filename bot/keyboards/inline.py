from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.locales import t


def decision_keyboard(request_id: int, lang: str, can_reject: bool = True):
    builder = InlineKeyboardBuilder()
    builder.button(
        text=t("btn_approve", lang), callback_data=f"decide:{request_id}:approved"
    )
    if can_reject:
        builder.button(
            text=t("btn_reject", lang), callback_data=f"decide:{request_id}:rejected"
        )
    builder.adjust(2)
    return builder.as_markup()


def coordinator_panel_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=t("filter_all", lang), callback_data="cpanel:all")
    builder.button(text=t("filter_new", lang), callback_data="cpanel:new")
    builder.button(text=t("filter_processed", lang), callback_data="cpanel:processed")
    builder.adjust(1)
    return builder.as_markup()


def requests_list_keyboard(requests):
    builder = InlineKeyboardBuilder()
    for r in requests:
        label = f"{r.user.last_name} {r.user.first_name} — {r.start_date}"
        builder.button(text=label, callback_data=f"cpanel_item:{r.id}")
    builder.adjust(1)
    return builder.as_markup()
