from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.filters import TextIs
from bot.keyboards.calendar import build_calendar
from bot.keyboards.inline import decision_keyboard
from bot.keyboards.menus import (
    confirm_keyboard,
    main_menu_keyboard,
    projects_keyboard,
    regions_keyboard,
    request_type_keyboard,
)
from bot.loader import bot
from bot.locales import t
from bot.states import RequestStates
from bot.utils import (
    create_absence_request,
    get_project,
    get_project_coordinators,
    get_regions,
    get_projects_by_region,
    get_user_by_telegram_id,
    save_notification_message_id,
)
from core.tasks import send_absence_request_email

router = Router()

L4_MAX_DAYS = 31


@router.message(TextIs("btn_new_request"))
async def new_request_start(message: Message, state: FSMContext):
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user:
        return
    await state.clear()
    await state.update_data(language=user.language)
    await state.set_state(RequestStates.choosing_type)
    await message.answer(t("choose_request_type", user.language), reply_markup=request_type_keyboard(user.language))


@router.callback_query(RequestStates.choosing_type, F.data.startswith("reqtype:"))
async def choose_type(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")
    action = callback.data.split(":")[1]

    if action == "cancel":
        await _cancel_flow(callback, state, lang)
        return

    regions = await get_regions()
    if not regions:
        await callback.message.edit_text(t("generic_error", lang))
        await callback.answer()
        return

    await state.update_data(request_type=action)
    await state.set_state(RequestStates.choosing_region)
    await callback.message.edit_text(t("choose_region", lang), reply_markup=regions_keyboard(regions))
    await callback.answer()


@router.callback_query(RequestStates.choosing_region, F.data.startswith("region:"))
async def choose_region(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")
    region_id = int(callback.data.split(":")[1])

    projects = await get_projects_by_region(region_id)
    if not projects:
        await callback.answer(t("generic_error", lang), show_alert=True)
        return

    await state.update_data(region_id=region_id)
    await state.set_state(RequestStates.choosing_project)
    await callback.message.edit_text(t("choose_project", lang), reply_markup=projects_keyboard(projects))
    await callback.answer()


@router.callback_query(RequestStates.choosing_project, F.data.startswith("project:"))
async def choose_project(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")
    project_id = int(callback.data.split(":")[1])
    project = await get_project(project_id)
    request_type = data["request_type"]

    # Ліміти: для L4 — 31 день, для вихідних — ліміт проєкту з Django Admin
    limit = L4_MAX_DAYS if request_type == "l4" else project.dayoff_limit

    today = date.today()
    await state.update_data(
        project_id=project_id, limit=limit, selected_dates=[], year=today.year, month=today.month,
    )
    await state.set_state(RequestStates.choosing_dates)

    key = "choose_dates_l4" if request_type == "l4" else "choose_dates_dayoff"
    await callback.message.edit_text(
        t(key, lang, limit=limit), reply_markup=build_calendar(today.year, today.month, set()),
    )
    await callback.answer()


@router.callback_query(RequestStates.choosing_dates, F.data.startswith("cal:"))
async def calendar_action(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")
    _, action, payload = callback.data.split(":", 2)
    selected = set(data.get("selected_dates", []))
    year, month = data.get("year"), data.get("month")

    if action == "ignore":
        await callback.answer()
        return

    if action == "cancel":
        await _cancel_flow(callback, state, lang)
        return

    if action in ("prev", "next"):
        year, month = map(int, payload.split("-"))
        await state.update_data(year=year, month=month)
        await callback.message.edit_reply_markup(reply_markup=build_calendar(year, month, selected))
        await callback.answer()
        return

    if action == "day":
        limit = data.get("limit")
        if payload in selected:
            selected.discard(payload)
        else:
            if len(selected) >= limit:
                await callback.answer(t("limit_exceeded", lang, limit=limit), show_alert=True)
                return
            selected.add(payload)
        await state.update_data(selected_dates=sorted(selected))
        await callback.message.edit_reply_markup(reply_markup=build_calendar(year, month, selected))
        await callback.answer()
        return

    if action == "done":
        if not selected:
            await callback.answer(t("choose_at_least_one_date", lang), show_alert=True)
            return

        project = await get_project(data["project_id"])
        request_type = data["request_type"]
        type_label = t("btn_l4", lang) if request_type == "l4" else t("btn_dayoff", lang)
        dates_sorted = sorted(selected)

        text = t(
            "confirm_request", lang,
            type=type_label, project=project.name, region=project.region.name,
            start=dates_sorted[0], end=dates_sorted[-1], count=len(dates_sorted),
        )
        await state.set_state(RequestStates.confirming)
        await callback.message.edit_text(text, reply_markup=confirm_keyboard(lang))
        await callback.answer()
        return


@router.callback_query(RequestStates.confirming, F.data.startswith("confirm:"))
async def confirm_request(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")
    action = callback.data.split(":")[1]
    user = await get_user_by_telegram_id(callback.from_user.id)

    if action == "no":
        await _cancel_flow(callback, state, lang)
        return

    req = await create_absence_request(
        user_id=user.id,
        project_id=data["project_id"],
        request_type=data["request_type"],
        dates=data["selected_dates"],
    )
    await state.clear()
    await callback.message.edit_text(t("request_created", lang))
    await callback.message.answer(t("main_menu_title", lang), reply_markup=main_menu_keyboard(lang, user.is_staff))
    await callback.answer()

    # Асинхронна email-розсилка (Celery)
    send_absence_request_email.delay(req.id)

    # Push-сповіщення координаторам проєкту з кнопками швидкої дії
    project = await get_project(data["project_id"])
    coordinators = await get_project_coordinators(data["project_id"])
    can_reject = data["request_type"] != "l4"
    profile_link = f"tg://user?id={user.telegram_id}"

    for coordinator in coordinators:
        c_lang = coordinator.language
        text = t(
            "coordinator_new_request_notification", c_lang,
            name=f"{user.last_name} {user.first_name}",
            link=profile_link,
            project=project.name, region=project.region.name,
            type=t("btn_l4", c_lang) if req.request_type == "l4" else t("btn_dayoff", c_lang),
            start=req.start_date, end=req.end_date,
        )
        try:
            sent = await bot.send_message(
                coordinator.telegram_id, text, reply_markup=decision_keyboard(req.id, c_lang, can_reject),
            )
            await save_notification_message_id(req.id, coordinator.telegram_id, sent.message_id)
        except Exception:
            # Координатор міг заблокувати бота тощо — не переривати обробку.
            pass


async def _cancel_flow(callback: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    user = await get_user_by_telegram_id(callback.from_user.id)
    await callback.message.edit_text(t("request_cancelled", lang))
    await callback.message.answer(
        t("main_menu_title", lang), reply_markup=main_menu_keyboard(lang, user.is_staff if user else False),
    )
    await callback.answer()
