import calendar as cal_module
from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]


def build_calendar(year: int, month: int, selected: set[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    today = date.today()

    builder.row(InlineKeyboardButton(
        text=f"{cal_module.month_name[month]} {year}", callback_data="cal:ignore:_",
    ))
    builder.row(*[InlineKeyboardButton(text=d, callback_data="cal:ignore:_") for d in WEEKDAYS])

    for week in cal_module.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="cal:ignore:_"))
                continue
            d = date(year, month, day)
            iso = d.isoformat()
            if d < today:
                # Заборона минулих дат (п.4.2, п.6 ТЗ)
                row.append(InlineKeyboardButton(text="·", callback_data="cal:ignore:_"))
            elif iso in selected:
                row.append(InlineKeyboardButton(text=f"✅{day}", callback_data=f"cal:day:{iso}"))
            else:
                row.append(InlineKeyboardButton(text=str(day), callback_data=f"cal:day:{iso}"))
        builder.row(*row)

    prev_month, prev_year = (12, year - 1) if month == 1 else (month - 1, year)
    next_month, next_year = (1, year + 1) if month == 12 else (month + 1, year)

    builder.row(
        InlineKeyboardButton(text="◀️", callback_data=f"cal:prev:{prev_year}-{prev_month:02d}"),
        InlineKeyboardButton(text=f"Обрано: {len(selected)}", callback_data="cal:ignore:_"),
        InlineKeyboardButton(text="▶️", callback_data=f"cal:next:{next_year}-{next_month:02d}"),
    )
    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data="cal:done:_"))
    builder.row(InlineKeyboardButton(text="❌ Скасувати", callback_data="cal:cancel:_"))
    return builder.as_markup()
