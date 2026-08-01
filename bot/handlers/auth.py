from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.menus import main_menu_keyboard
from bot.locales import t
from bot.states import LoginStates, RegistrationStates
from bot.utils import (
    create_user,
    get_user_by_email,
    is_valid_email,
    is_valid_name,
    link_telegram_and_check_password,
)

router = Router()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "auth:register")
async def start_registration(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")
    await state.set_state(RegistrationStates.first_name)
    await callback.message.edit_text(t("reg_ask_first_name", lang))
    await callback.answer()


@router.message(RegistrationStates.first_name)
async def reg_first_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")
    value = (message.text or "").strip()
    if not is_valid_name(value):
        await message.answer(t("reg_invalid_name", lang))
        return
    await state.update_data(first_name=value)
    await state.set_state(RegistrationStates.last_name)
    await message.answer(t("reg_ask_last_name", lang))


@router.message(RegistrationStates.last_name)
async def reg_last_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")
    value = (message.text or "").strip()
    if not is_valid_name(value):
        await message.answer(t("reg_invalid_name", lang))
        return
    await state.update_data(last_name=value)
    await state.set_state(RegistrationStates.email)
    await message.answer(t("reg_ask_email", lang))


@router.message(RegistrationStates.email)
async def reg_email(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")
    email = (message.text or "").strip()
    if not is_valid_email(email):
        await message.answer(t("reg_invalid_email", lang))
        return
    existing = await get_user_by_email(email)
    if existing:
        await message.answer(t("reg_email_exists", lang))
        return
    await state.update_data(email=email)
    await state.set_state(RegistrationStates.phone)
    await message.answer(t("reg_ask_phone", lang))


@router.message(RegistrationStates.phone)
async def reg_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")
    await state.update_data(phone=(message.text or "").strip())
    await state.set_state(RegistrationStates.password)
    await message.answer(t("reg_ask_password", lang))


@router.message(RegistrationStates.password)
async def reg_password(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")
    password = message.text or ""

    user = await create_user(
        telegram_id=message.from_user.id,
        first_name=data["first_name"],
        last_name=data["last_name"],
        email=data["email"],
        phone=data["phone"],
        password=password,
        language=lang,
    )

    # UI Security: Removing the Password from the Message
    try:
        await message.delete()
    except Exception:
        pass

    await state.clear()
    await message.answer(
        t("reg_success", lang), reply_markup=main_menu_keyboard(lang, user.is_staff)
    )


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "auth:login")
async def start_login(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")
    await state.set_state(LoginStates.email)
    await callback.message.edit_text(t("login_ask_email", lang))
    await callback.answer()


@router.message(LoginStates.email)
async def login_email(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")
    await state.update_data(login_email=(message.text or "").strip())
    await state.set_state(LoginStates.password)
    await message.answer(t("login_ask_password", lang))


@router.message(LoginStates.password)
async def login_password(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")

    user = await link_telegram_and_check_password(
        data["login_email"],
        message.text or "",
        message.from_user.id,
    )

    # UI Security: Removing the Password from the Message
    try:
        await message.delete()
    except Exception:
        pass

    if not user:
        await message.answer(t("login_failed", lang))
        return

    await state.clear()
    await message.answer(
        t("login_success", user.language),
        reply_markup=main_menu_keyboard(user.language, user.is_staff),
    )
