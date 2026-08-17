from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.filters import TextIs
from bot.keyboards.inline import no_access_keyboard
from bot.keyboards.menus import language_keyboard, main_menu_keyboard
from bot.locales import t
from bot.utils import get_user_by_telegram_id, set_user_language

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(t("choose_language", "uk"), reply_markup=language_keyboard())


@router.message(TextIs("btn_language"))
async def change_language(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(t("choose_language", "uk"), reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def choose_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split(":")[1]
    await state.update_data(language=lang)

    user = await get_user_by_telegram_id(callback.from_user.id)

    if user and user.is_active:
        await set_user_language(callback.from_user.id, lang)
        await callback.message.edit_text(t("lang_set", lang))
        await callback.message.answer(
            t("main_menu_title", lang),
            reply_markup=main_menu_keyboard(lang, user.is_staff),
        )
    else:
        # Користувача немає в базі АБО is_active=False — доступ заборонено.
        await callback.message.edit_text(
            t("access_denied", lang),
            reply_markup=no_access_keyboard(lang),
        )
    await callback.answer()


@router.callback_query(F.data == "myid:show")
async def show_my_id(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")
    await callback.message.answer(t("my_id_template", lang, id=callback.from_user.id))
    await callback.answer()
