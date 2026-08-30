from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.menus import confirm_keyboard, main_menu_keyboard
from bot.locales import t
from bot.states import ServiceRequestStates
from bot.utils import create_service_request, get_active_user_by_telegram_id

from core.tasks import send_service_request_email

router = Router()


@router.message(ServiceRequestStates.entering_text)
async def service_request_text(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")
    text = (message.text or "").strip()

    if not text:
        await message.answer(t("service_request_empty", lang))
        return

    await state.update_data(service_request_text=text)
    await state.set_state(ServiceRequestStates.confirming)

    request_type = data["service_request_type"]
    type_label = (
        t("btn_administration", lang)
        if request_type == "administration"
        else t("btn_accounting", lang)
    )
    preview = text if len(text) <= 300 else text[:297] + "..."

    confirm_text = t("service_request_confirm", lang, type=type_label, text=preview)
    await message.answer(confirm_text, reply_markup=confirm_keyboard(lang))


@router.callback_query(ServiceRequestStates.confirming, F.data.startswith("confirm:"))
async def service_request_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")
    action = callback.data.split(":")[1]
    user = await get_active_user_by_telegram_id(callback.from_user.id)

    if action == "no" or not user:
        await state.clear()
        await callback.message.edit_text(t("request_cancelled", lang))
        if user:
            await callback.message.answer(
                t("main_menu_title", lang),
                reply_markup=main_menu_keyboard(lang, user.is_staff),
            )
        await callback.answer()
        return

    service_request = await create_service_request(
        user_id=user.id,
        request_type=data["service_request_type"],
        text=data["service_request_text"],
    )
    await state.clear()
    await callback.message.edit_text(t("request_created", lang))
    await callback.message.answer(
        t("main_menu_title", lang),
        reply_markup=main_menu_keyboard(lang, user.is_staff),
    )
    await callback.answer()

    send_service_request_email.delay(service_request.id)
