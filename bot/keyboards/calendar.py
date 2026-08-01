import calendar as cal_module
from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.locales import t

_WEEKDAYS = {
    "uk": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"],
    "pl": ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Ndz"],
    "en": ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
    "ru": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
}

_MONTHS = {
    "uk": [
        "",
        "Січень",
        "Лютий",
        "Березень",
        "Квітень",
        "Травень",
        "Червень",
        "Липень",
        "Серпень",
        "Вересень",
        "Жовтень",
        "Листопад",
        "Грудень",
    ],
    "pl": [
        "",
        "Styczeń",
        "Luty",
        "Marzec",
        "Kwiecień",
        "Maj",
        "Czerwiec",
        "Lipiec",
        "Sierpień",
        "Wrzesień",
        "Październik",
        "Listopad",
        "Grudzień",
    ],
    "en": [
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ],
    "ru": [
        "",
        "Январь",
        "Февраль",
        "Март",
        "Апрель",
        "Май",
        "Июнь",
        "Июль",
        "Август",
        "Сентябрь",
        "Октябрь",
        "Ноябрь",
        "Декабрь",
    ],
}


def build_calendar(
    year: int, month: int, selected: set[str], lang: str = "uk"
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    today = date.today()
    weekdays = _WEEKDAYS.get(lang, _WEEKDAYS["uk"])
    months = _MONTHS.get(lang, _MONTHS["uk"])

    builder.row(
        InlineKeyboardButton(
            text=f"{months[month]} {year}",
            callback_data="cal:ignore:_",
        )
    )
    builder.row(
        *[InlineKeyboardButton(text=d, callback_data="cal:ignore:_") for d in weekdays]
    )

    for week in cal_module.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="cal:ignore:_"))
                continue
            d = date(year, month, day)
            iso = d.isoformat()
            if d < today:
                # Ban on past dates
                row.append(InlineKeyboardButton(text="·", callback_data="cal:ignore:_"))
            elif iso in selected:
                row.append(
                    InlineKeyboardButton(
                        text=f"✅{day}", callback_data=f"cal:day:{iso}"
                    )
                )
            else:
                row.append(
                    InlineKeyboardButton(text=str(day), callback_data=f"cal:day:{iso}")
                )
        builder.row(*row)

    prev_month, prev_year = (12, year - 1) if month == 1 else (month - 1, year)
    next_month, next_year = (1, year + 1) if month == 12 else (month + 1, year)

    builder.row(
        InlineKeyboardButton(
            text="◀️", callback_data=f"cal:prev:{prev_year}-{prev_month:02d}"
        ),
        InlineKeyboardButton(
            text=t("calendar_selected_count", lang, count=len(selected)),
            callback_data="cal:ignore:_",
        ),
        InlineKeyboardButton(
            text="▶️", callback_data=f"cal:next:{next_year}-{next_month:02d}"
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=t("btn_calendar_done", lang), callback_data="cal:done:_"
        )
    )
    builder.row(
        InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="cal:cancel:_")
    )
    return builder.as_markup()
