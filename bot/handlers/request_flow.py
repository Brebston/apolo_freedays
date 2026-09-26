from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from django.conf import settings
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
from bot.states import RequestStates, ServiceRequestStates
from bot.utils import (
    create_absence_request,
    get_date_capacity_limit,
    get_project,
    get_project_coordinators,
    get_regions,
    get_projects_by_region,
    get_used_dayoff_days_in_month,
    get_active_user_by_telegram_id,
    get_workers_count_on_date,
    save_notification_message_id,
)

from core.tasks import send_absence_request_email

router = Router()

L4_MAX_DAYS = 31


@router.message(TextIs("btn_new_request"))
async def new_request_start(message: Message, state: FSMContext):
    user = await get_active_user_by_telegram_id(message.from_user.id)
    if not user:
        return
    await state.clear()
    await state.update_data(language=user.language, user_id=user.id)
    await state.set_state(RequestStates.choosing_type)
    await message.answer(
        t("choose_request_type", user.language),
        reply_markup=request_type_keyboard(user.language),
    )


@router.callback_query(RequestStates.choosing_type, F.data.startswith("reqtype:"))
async def choose_type(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")
    action = callback.data.split(":")[1]

    if action == "cancel":
        await _cancel_flow(callback, state, lang)
        return

    if action in ("administration", "accounting"):
        await state.update_data(service_request_type=action)
        await state.set_state(ServiceRequestStates.entering_text)
        prompt_key = (
            "service_request_prompt_administration"
            if action == "administration"
            else "service_request_prompt_accounting"
        )
        await callback.message.edit_text(t(prompt_key, lang))
        await callback.answer()
        return

    regions = await get_regions()

    if not regions:
        await callback.message.edit_text(t("generic_error", lang))
        await callback.answer()
        return

    await state.update_data(request_type=action)
    await state.set_state(RequestStates.choosing_region)
    await callback.message.edit_text(
        t("choose_region", lang), reply_markup=regions_keyboard(regions)
    )
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
    await callback.message.edit_text(
        t("choose_project", lang), reply_markup=projects_keyboard(projects)
    )
    await callback.answer()


@router.callback_query(RequestStates.choosing_project, F.data.startswith("project:"))
async def choose_project(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uk")
    project_id = int(callback.data.split(":")[1])
    project = await get_project(project_id)
    request_type = data["request_type"]

    # Limits: 31 days for L4; for weekends — the project's monthly limit from Django Admin.
    limit = L4_MAX_DAYS if request_type == "l4" else project.dayoff_limit
    # Employee limit per date (weekends only; None = no limits)
    capacity_limit = None if request_type == "l4" else project.max_workers_per_day

    today = date.today()
    await state.update_data(
        project_id=project_id,
        limit=limit,
        capacity_limit=capacity_limit,
        selected_dates=[],
        year=today.year,
        month=today.month,
    )
    await state.set_state(RequestStates.choosing_dates)

    key = "choose_dates_l4" if request_type == "l4" else "choose_dates_dayoff"
    await callback.message.edit_text(
        t(key, lang, limit=limit),
        reply_markup=build_calendar(today.year, today.month, set(), lang),
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
        await callback.message.edit_reply_markup(
            reply_markup=build_calendar(year, month, selected, lang)
        )
        await callback.answer()
        return

    if action == "day":
        request_type = data["request_type"]
        limit = data.get("limit")

        if payload in selected:
            selected.discard(payload)
        else:
            d = date.fromisoformat(payload)

            if request_type == "l4":
                if len(selected) >= limit:
                    await callback.answer(
                        t("limit_exceeded", lang, limit=limit), show_alert=True
                    )
                    return
            else:
                already_in_month = sum(
                    1
                    for iso in selected
                    if iso.startswith(f"{d.year:04d}-{d.month:02d}")
                )
                used_in_month = await get_used_dayoff_days_in_month(
                    data["user_id"],
                    data["project_id"],
                    d.year,
                    d.month,
                )
                if used_in_month + already_in_month + 1 > limit:
                    month_label = f"{d.month:02d}.{d.year:04d}"
                    await callback.answer(
                        t(
                            "monthly_limit_exceeded",
                            lang,
                            limit=limit,
                            used=used_in_month,
                            month=month_label,
                        ),
                        show_alert=True,
                    )
                    return

                # Limit on the number of employees who can be absent
                # simultaneously on a single day (Project.max_workers_per_day).
                # Limit on the number of employees who can be absent
                # simultaneously on a single day (Project.max_workers_per_day).
                # Limit on the number of employees for a specific date: first, we check
                # if there is an override (ProjectDateLimit) for this specific date
                # in the Django Admin; otherwise, the general project limit applies.

                date_override = await get_date_capacity_limit(
                    data["project_id"], payload
                )
                effective_capacity = (
                    date_override
                    if date_override is not None
                    else data.get("capacity_limit")
                )
                if effective_capacity is not None:
                    workers_count = await get_workers_count_on_date(
                        data["project_id"], payload
                    )
                    if workers_count >= effective_capacity:
                        await callback.answer(
                            t(
                                "date_capacity_full",
                                lang,
                                date=payload,
                                limit=effective_capacity,
                            ),
                            show_alert=True,
                        )
                        return

            selected.add(payload)

        await state.update_data(selected_dates=sorted(selected))
        await callback.message.edit_reply_markup(
            reply_markup=build_calendar(year, month, selected, lang)
        )
        await callback.answer()
        return

    if action == "done":
        if not selected:
            await callback.answer(t("choose_at_least_one_date", lang), show_alert=True)
            return

        project = await get_project(data["project_id"])
        request_type = data["request_type"]
        type_label = (
            t("btn_l4", lang) if request_type == "l4" else t("btn_dayoff", lang)
        )
        dates_sorted = sorted(selected)

        text = t(
            "confirm_request",
            lang,
            type=type_label,
            project=project.name,
            region=project.region.name,
            start=dates_sorted[0],
            end=dates_sorted[-1],
            count=len(dates_sorted),
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
    user = await get_active_user_by_telegram_id(callback.from_user.id)

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
    if data["request_type"] == "l4":
        reminder_markup = None
        if settings.WEBAPP_URL:
            reminder_markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=t("btn_open_app", lang),
                            web_app=WebAppInfo(url=settings.WEBAPP_URL),
                        ),
                    ]
                ]
            )
        await callback.message.answer(
            t("l4_attach_reminder", lang), reply_markup=reminder_markup
        )
    await callback.message.answer(
        t("main_menu_title", lang), reply_markup=main_menu_keyboard(lang, user.is_staff)
    )
    await callback.answer()

    # Asynchronous email dispatch (Celery)
    send_absence_request_email.delay(req.id)

    # Push notifications to project coordinators with quick-action buttons
    project = await get_project(data["project_id"])
    coordinators = await get_project_coordinators(data["project_id"])
    can_reject = data["request_type"] != "l4"
    profile_link = f"tg://user?id={user.telegram_id}"

    for coordinator in coordinators:
        c_lang = coordinator.language
        text = t(
            "coordinator_new_request_notification",
            c_lang,
            name=f"{user.last_name} {user.first_name}",
            link=profile_link,
            project=project.name,
            region=project.region.name,
            type=(
                t("btn_l4", c_lang)
                if req.request_type == "l4"
                else t("btn_dayoff", c_lang)
            ),
            start=req.start_date,
            end=req.end_date,
        )
        try:
            sent = await bot.send_message(
                coordinator.telegram_id,
                text,
                reply_markup=decision_keyboard(req.id, c_lang, can_reject),
            )
            await save_notification_message_id(
                req.id, coordinator.telegram_id, sent.message_id
            )
        except Exception:
            # The coordinator could block the bot, etc., without interrupting processing.
            pass


async def _cancel_flow(callback: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    user = await get_active_user_by_telegram_id(callback.from_user.id)
    await callback.message.edit_text(t("request_cancelled", lang))
    await callback.message.answer(
        t("main_menu_title", lang),
        reply_markup=main_menu_keyboard(lang, user.is_staff if user else False),
    )
    await callback.answer()
