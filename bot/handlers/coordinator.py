from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.filters import TextIs
from bot.keyboards.inline import (
    coordinator_panel_keyboard,
    decision_keyboard,
    requests_list_keyboard,
)
from bot.loader import bot
from bot.locales import t
from bot.utils import (
    decide_request,
    get_coordinator_project_ids,
    get_project_requests,
    get_request,
    get_user_by_telegram_id,
)
from core.models import RequestStatus

router = Router()


@router.message(TextIs("btn_coordinator_panel"))
async def coordinator_panel(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user or not user.is_staff:
        return
    await message.answer(
        t("coordinator_panel_title", user.language),
        reply_markup=coordinator_panel_keyboard(user.language),
    )


@router.callback_query(F.data.startswith("cpanel:"))
async def coordinator_panel_filter(callback: CallbackQuery):
    user = await get_user_by_telegram_id(callback.from_user.id)
    if not user or not user.is_staff:
        await callback.answer()
        return

    status_filter = callback.data.split(":")[1]
    project_ids = await get_coordinator_project_ids(user.id)
    requests = await get_project_requests(
        project_ids, None if status_filter == "all" else status_filter
    )

    if not requests:
        await callback.answer(t("no_requests", user.language), show_alert=True)
        return

    await callback.message.edit_text(
        t("my_requests_title", user.language),
        reply_markup=requests_list_keyboard(requests),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cpanel_item:"))
async def coordinator_panel_item(callback: CallbackQuery):
    user = await get_user_by_telegram_id(callback.from_user.id)
    if not user or not user.is_staff:
        await callback.answer()
        return

    request_id = int(callback.data.split(":")[1])
    req = await get_request(request_id)
    if not req:
        await callback.answer(t("generic_error", user.language), show_alert=True)
        return

    can_reject = req.can_be_rejected() and req.status == RequestStatus.PENDING
    text = t(
        "request_item_detail",
        user.language,
        name=f"{req.user.last_name} {req.user.first_name}",
        project=req.project.name,
        region=req.project.region.name,
        type=(
            t("btn_l4", user.language)
            if req.request_type == "l4"
            else t("btn_dayoff", user.language)
        ),
        start=req.start_date,
        end=req.end_date,
        status=t(f"status_{req.status}", user.language),
    )
    kb = (
        decision_keyboard(req.id, user.language, can_reject)
        if req.status == RequestStatus.PENDING
        else None
    )
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("decide:"))
async def decide(callback: CallbackQuery):
    """
    Handles "Confirm"/"Reject" clicks — whether from a push notification
    about a new request or from the coordinator panel.
    """
    coordinator = await get_user_by_telegram_id(callback.from_user.id)
    if not coordinator or not coordinator.is_staff:
        await callback.answer()
        return

    _, request_id, new_status = callback.data.split(":")
    request_id = int(request_id)

    req_before = await get_request(request_id)
    if not req_before:
        await callback.answer(t("generic_error", coordinator.language), show_alert=True)
        return

    # L4 cannot be rejected — the rule is mandatory.
    if new_status == "rejected" and not req_before.can_be_rejected():
        await callback.answer(
            t("l4_cannot_reject", coordinator.language), show_alert=True
        )
        return

    req, changed = await decide_request(request_id, new_status, coordinator.id)
    if not changed:
        await callback.answer(
            t("already_decided", coordinator.language), show_alert=True
        )
        return

    status_label = t(f"status_{new_status}", coordinator.language)
    try:
        base_text = callback.message.text or callback.message.caption or ""
        await callback.message.edit_text(
            f"{base_text}\n\n➡️ {status_label}", reply_markup=None
        )
    except Exception:
        pass
    await callback.answer(t("decision_saved", coordinator.language))

    # Immediate push notification to the employee regarding the decision.
    worker = req.user
    text = t(
        "request_decided_worker",
        worker.language,
        status=t(f"status_{new_status}", worker.language),
        start=req.start_date,
        end=req.end_date,
        project=req.project.name,
    )
    if worker.telegram_id:
        try:
            await bot.send_message(worker.telegram_id, text)
        except Exception:
            pass
