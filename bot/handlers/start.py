from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.filters import TextIs
from bot.keyboards.menus import auth_keyboard, language_keyboard, main_menu_keyboard
from bot.locales import t
from bot.utils import get_user_by_telegram_id, set_user_language

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user_by_telegram_id(message.from_user.id)
    if user:
        await state.update_data(language=user.language)
        await message.answer(
            t("main_menu_title", user.language),
            reply_markup=main_menu_keyboard(user.language, user.is_staff),
        )
    else:
        await message.answer(t("choose_language", "uk"), reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def choose_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split(":")[1]
    await state.update_data(language=lang)
    user = await get_user_by_telegram_id(callback.from_user.id)
    if user:
        await set_user_language(callback.from_user.id, lang)
        await callback.message.edit_text(t("lang_set", lang))
        await callback.message.answer(
            t("main_menu_title", lang), reply_markup=main_menu_keyboard(lang, user.is_staff),
        )
    else:
        await callback.message.edit_text(t("welcome", lang), reply_markup=auth_keyboard(lang))
    await callback.answer()


@router.message(TextIs("btn_language"))
async def change_language(message: Message):
    await message.answer(t("choose_language", "uk"), reply_markup=language_keyboard())
