from aiogram import Router
from aiogram.types import Message

from bot.filters import TextIs
from bot.locales import t
from bot.utils import (
    get_active_user_by_telegram_id,
    get_coordinators_by_region,
    get_my_all_requests,
    get_regions,
)

router = Router()


@router.message(TextIs("btn_my_requests"))
async def my_requests(message: Message):
    user = await get_active_user_by_telegram_id(message.from_user.id)
    if not user:
        return
    requests = await get_my_all_requests(user.id)
    if not requests:
        await message.answer(t("no_requests", user.language))
        return

    lines = [t("my_requests_title", user.language), ""]
    for r in requests:
        status_label = t(f"status_{r.status}", user.language)

        if r.kind == "absence":
            type_label = (
                t("btn_l4", user.language)
                if r.request_type == "l4"
                else t("btn_dayoff", user.language)
            )
            lines.append(
                t(
                    "request_item",
                    user.language,
                    type=type_label,
                    start=r.start_date,
                    end=r.end_date,
                    project=r.project.name,
                    status=status_label,
                )
            )
        else:
            type_label = (
                t("btn_administration", user.language)
                if r.request_type == "administration"
                else t("btn_accounting", user.language)
            )
            preview = r.text if len(r.text) <= 60 else r.text[:57] + "..."
            lines.append(
                t(
                    "service_request_item",
                    user.language,
                    type=type_label,
                    text=preview,
                    status=status_label,
                )
            )

    await message.answer("\n".join(lines))


@router.message(TextIs("btn_coordinators"))
async def coordinators_contacts(message: Message):
    user = await get_active_user_by_telegram_id(message.from_user.id)
    if not user:
        return
    regions = await get_regions()
    lines = [t("coordinators_list_title", user.language), ""]
    any_found = False
    for region in regions:
        coords = await get_coordinators_by_region(region.id)
        if not coords:
            continue
        any_found = True
        lines.append(f"📍 {region.name}")
        for c in coords:
            contact = (
                f"@{c.username}"
                if c.username and "@" not in c.username
                else (c.phone or c.email)
            )
            lines.append(f"  • {c.last_name} {c.first_name} — {contact}")
        lines.append("")
    if not any_found:
        await message.answer(t("no_requests", user.language))
        return
    await message.answer("\n".join(lines))
