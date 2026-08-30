from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from bot.locales import t


def language_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇦 Українська", callback_data="lang:uk")
    builder.button(text="🇵🇱 Polski", callback_data="lang:pl")
    builder.button(text="🇬🇧 English", callback_data="lang:en")
    builder.button(text="🇷🇺 Русский", callback_data="lang:ru")
    builder.adjust(2)
    return builder.as_markup()


def main_menu_keyboard(lang: str, is_staff: bool):
    builder = ReplyKeyboardBuilder()
    builder.button(text=t("btn_new_request", lang))
    builder.button(text=t("btn_my_requests", lang))
    builder.button(text=t("btn_coordinators", lang))
    builder.button(text=t("btn_language", lang))
    if is_staff:
        builder.button(text=t("btn_coordinator_panel", lang))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def request_type_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_dayoff", lang), callback_data="reqtype:dayoff")
    builder.button(text=t("btn_l4", lang), callback_data="reqtype:l4")
    builder.button(
        text=t("btn_administration", lang), callback_data="reqtype:administration"
    )
    builder.button(text=t("btn_accounting", lang), callback_data="reqtype:accounting")
    builder.button(text=t("btn_cancel", lang), callback_data="reqtype:cancel")
    builder.adjust(1)
    return builder.as_markup()


def regions_keyboard(regions):
    builder = InlineKeyboardBuilder()
    for r in regions:
        builder.button(text=r.name, callback_data=f"region:{r.id}")
    builder.adjust(2)
    return builder.as_markup()


def projects_keyboard(projects):
    builder = InlineKeyboardBuilder()
    for p in projects:
        builder.button(text=p.name, callback_data=f"project:{p.id}")
    builder.adjust(1)
    return builder.as_markup()


def confirm_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_confirm", lang), callback_data="confirm:yes")
    builder.button(text=t("btn_cancel", lang), callback_data="confirm:no")
    builder.adjust(2)
    return builder.as_markup()


def no_access_reply_keyboard(lang: str):
    """For a user without access, the reply keyboard consists only of a language-switching button."""
    builder = ReplyKeyboardBuilder()
    builder.button(text=t("btn_language", lang))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)
