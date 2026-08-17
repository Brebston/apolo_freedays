"""
A simple, key-based translation store.
t("key", lang, **kwargs) -> str
"""

TEXTS = {
    "choose_language": {
        "uk": "Оберіть мову інтерфейсу:",
        "pl": "Wybierz język interfejsu:",
        "en": "Choose your interface language:",
        "ru": "Выберите язык интерфейса:",
    },
    "lang_set": {
        "uk": "✅ Мову змінено на українську.",
        "pl": "✅ Język ustawiono na polski.",
        "en": "✅ Language set to English.",
        "ru": "✅ Язык изменён на русский.",
    },
    "access_denied": {
        "uk": "⛔ У вас немає доступу до бота.\nЗверніться до координатора, щоб отримати доступ.",
        "pl": "⛔ Nie masz dostępu do bota.\nSkontaktuj się z koordynatorem, aby uzyskać dostęp.",
        "en": "⛔ You don't have access to this bot.\nContact your coordinator to get access.",
        "ru": "⛔ У вас нет доступа к боту.\nОбратитесь к координатору, чтобы получить доступ.",
    },
    "btn_show_my_id": {
        "uk": "🆔 Дізнатися свій Telegram ID",
        "pl": "🆔 Sprawdź swój Telegram ID",
        "en": "🆔 Get my Telegram ID",
        "ru": "🆔 Узнать свой Telegram ID",
    },
    "my_id_template": {
        "uk": (
            "Перешліть це повідомлення координатору, щоб отримати доступ до бота:\n\n"
            "👤 Мій Telegram ID: {id}\n\n"
            "Прошу надати мені доступ до бота обліку відсутностей."
        ),
        "pl": (
            "Prześlij tę wiadomość do koordynatora, aby uzyskać dostęp do bota:\n\n"
            "👤 Mój Telegram ID: {id}\n\n"
            "Proszę o nadanie mi dostępu do bota ewidencji nieobecności."
        ),
        "en": (
            "Forward this message to your coordinator to get access to the bot:\n\n"
            "👤 My Telegram ID: {id}\n\n"
            "Please grant me access to the absence-tracking bot."
        ),
        "ru": (
            "Перешлите это сообщение координатору, чтобы получить доступ к боту:\n\n"
            "👤 Мой Telegram ID: {id}\n\n"
            "Прошу предоставить мне доступ к боту учёта отсутствий."
        ),
    },
    "main_menu_title": {
        "uk": "Головне меню:",
        "pl": "Menu główne:",
        "en": "Main menu:",
        "ru": "Главное меню:",
    },
    "btn_new_request": {
        "uk": "➕ Подати зголошення",
        "pl": "➕ Nowe zgłoszenie",
        "en": "➕ New request",
        "ru": "➕ Подать заявку",
    },
    "btn_my_requests": {
        "uk": "📋 Мої зголошення",
        "pl": "📋 Moje zgłoszenia",
        "en": "📋 My requests",
        "ru": "📋 Мои заявки",
    },
    "btn_coordinators": {
        "uk": "☎️ Координатори",
        "pl": "☎️ Koordynatorzy",
        "en": "☎️ Coordinators",
        "ru": "☎️ Координаторы",
    },
    "btn_language": {
        "uk": "🌐 Мова",
        "pl": "🌐 Język",
        "en": "🌐 Language",
        "ru": "🌐 Язык",
    },
    "btn_coordinator_panel": {
        "uk": "🗂 Панель координатора",
        "pl": "🗂 Panel koordynatora",
        "en": "🗂 Coordinator panel",
        "ru": "🗂 Панель координатора",
    },
    "btn_cancel": {
        "uk": "❌ Скасувати",
        "pl": "❌ Anuluj",
        "en": "❌ Cancel",
        "ru": "❌ Отмена",
    },
    "btn_calendar_done": {
        "uk": "✅ Готово",
        "pl": "✅ Gotowe",
        "en": "✅ Done",
        "ru": "✅ Готово",
    },
    "calendar_selected_count": {
        "uk": "Обрано: {count}",
        "pl": "Wybrano: {count}",
        "en": "Selected: {count}",
        "ru": "Выбрано: {count}",
    },
    "choose_request_type": {
        "uk": "Оберіть тип зголошення:",
        "pl": "Wybierz typ zgłoszenia:",
        "en": "Choose the request type:",
        "ru": "Выберите тип заявки:",
    },
    "btn_dayoff": {
        "uk": "🏖 Вихідний день",
        "pl": "🏖 Dzień wolny",
        "en": "🏖 Day off",
        "ru": "🏖 Выходной день",
    },
    "btn_l4": {
        "uk": "🤒 Лікарняний (L4)",
        "pl": "🤒 Zwolnienie (L4)",
        "en": "🤒 Sick leave (L4)",
        "ru": "🤒 Больничный (L4)",
    },
    "choose_region": {
        "uk": "Оберіть регіон:",
        "pl": "Wybierz region:",
        "en": "Choose a region:",
        "ru": "Выберите регион:",
    },
    "choose_project": {
        "uk": "Оберіть проєкт:",
        "pl": "Wybierz projekt:",
        "en": "Choose a project:",
        "ru": "Выберите проект:",
    },
    "choose_dates_dayoff": {
        "uk": "Оберіть дати вихідних. Місячний ліміт проєкту: {limit} дн./міс. Минулі дати недоступні.",
        "pl": "Wybierz daty. Miesięczny limit projektu: {limit} dni/mies. Przeszłe daty są niedostępne.",
        "en": "Select dates. Project's monthly limit: {limit} days/month. Past dates are disabled.",
        "ru": "Выберите даты. Месячный лимит проекта: {limit} дн./мес. Прошедшие даты недоступны.",
    },
    "choose_dates_l4": {
        "uk": "Оберіть дати лікарняного (максимум {limit} дн.).",
        "pl": "Wybierz daty zwolnienia L4 (maksymalnie {limit} dni).",
        "en": "Select the sick-leave dates (maximum {limit} days).",
        "ru": "Выберите даты больничного (максимум {limit} дн.).",
    },
    "limit_exceeded": {
        "uk": "⚠️ Перевищено ліміт: максимум {limit} дн.",
        "pl": "⚠️ Przekroczono limit: maksymalnie {limit} dni.",
        "en": "⚠️ Limit exceeded: maximum {limit} days.",
        "ru": "⚠️ Превышен лимит: максимум {limit} дн.",
    },
    "choose_at_least_one_date": {
        "uk": "Оберіть хоча б одну дату.",
        "pl": "Wybierz przynajmniej jedną datę.",
        "en": "Select at least one date.",
        "ru": "Выберите хотя бы одну дату.",
    },
    "monthly_limit_exceeded": {
        "uk": "⚠️ Місячний ліміт вихідних для цього проєкту — {limit} дн. У {month} вже використано {used} дн.",
        "pl": "⚠️ Miesięczny limit dni wolnych dla tego projektu to {limit} dni. W {month} wykorzystano już {used} dni.",
        "en": "⚠️ The monthly day-off limit for this project is {limit} days. {used} days already used in {month}.",
        "ru": "⚠️ Месячный лимит выходных для этого проекта — {limit} дн. В {month} уже использовано {used} дн.",
    },
    "date_capacity_full": {
        "uk": "⚠️ На {date} вже досягнуто ліміту працівників на вихідному ({limit}). Оберіть іншу дату.",
        "pl": "⚠️ Na dzień {date} osiągnięto limit pracowników na urlopie ({limit}). Wybierz inną datę.",
        "en": "⚠️ The worker limit for {date} has been reached ({limit}). Please choose another date.",
        "ru": "⚠️ На {date} уже достигнут лимит работников на выходном ({limit}). Выберите другую дату.",
    },
    "confirm_request": {
        "uk": "Перевірте деталі зголошення:\n\nТип: {type}\nПроєкт: {project} ({region})\nДати: {start} — {end}\nКількість днів: {count}",
        "pl": "Sprawdź szczegóły zgłoszenia:\n\nTyp: {type}\nProjekt: {project} ({region})\nDaty: {start} — {end}\nLiczba dni: {count}",
        "en": "Please review the request details:\n\nType: {type}\nProject: {project} ({region})\nDates: {start} — {end}\nDays: {count}",
        "ru": "Проверьте детали заявки:\n\nТип: {type}\nПроект: {project} ({region})\nДаты: {start} — {end}\nКоличество дней: {count}",
    },
    "btn_confirm": {
        "uk": "✅ Підтвердити",
        "pl": "✅ Potwierdź",
        "en": "✅ Confirm",
        "ru": "✅ Подтвердить",
    },
    "request_created": {
        "uk": "✅ Зголошення подано! Координатор отримав сповіщення.",
        "pl": "✅ Zgłoszenie wysłane! Koordynator otrzymał powiadomienie.",
        "en": "✅ Request submitted! The coordinator has been notified.",
        "ru": "✅ Заявка подана! Координатор получил уведомление.",
    },
    "request_cancelled": {
        "uk": "Скасовано.",
        "pl": "Anulowano.",
        "en": "Cancelled.",
        "ru": "Отменено.",
    },
    "no_requests": {
        "uk": "Записів не знайдено.",
        "pl": "Nie znaleziono wpisów.",
        "en": "No records found.",
        "ru": "Записей не найдено.",
    },
    "my_requests_title": {
        "uk": "📋 Ваші зголошення:",
        "pl": "📋 Twoje zgłoszenia:",
        "en": "📋 Your requests:",
        "ru": "📋 Ваши заявки:",
    },
    "request_item": {
        "uk": "• {type} | {project} | {start} — {end} | Статус: {status}",
        "pl": "• {type} | {project} | {start} — {end} | Status: {status}",
        "en": "• {type} | {project} | {start} — {end} | Status: {status}",
        "ru": "• {type} | {project} | {start} — {end} | Статус: {status}",
    },
    "request_item_detail": {
        "uk": "👤 {name}\nПроєкт: {project} ({region})\nТип: {type}\nДати: {start} — {end}\nСтатус: {status}",
        "pl": "👤 {name}\nProjekt: {project} ({region})\nTyp: {type}\nDaty: {start} — {end}\nStatus: {status}",
        "en": "👤 {name}\nProject: {project} ({region})\nType: {type}\nDates: {start} — {end}\nStatus: {status}",
        "ru": "👤 {name}\nПроект: {project} ({region})\nТип: {type}\nДаты: {start} — {end}\nСтатус: {status}",
    },
    "status_pending": {
        "uk": "⏳ Очікує",
        "pl": "⏳ Oczekuje",
        "en": "⏳ Pending",
        "ru": "⏳ Ожидает",
    },
    "status_approved": {
        "uk": "✅ Підтверджено",
        "pl": "✅ Zatwierdzono",
        "en": "✅ Approved",
        "ru": "✅ Подтверждено",
    },
    "status_rejected": {
        "uk": "❌ Відхилено",
        "pl": "❌ Odrzucono",
        "en": "❌ Rejected",
        "ru": "❌ Отклонено",
    },
    "coordinators_list_title": {
        "uk": "☎️ Контакти координаторів за регіонами:",
        "pl": "☎️ Kontakty koordynatorów wg regionów:",
        "en": "☎️ Coordinator contacts by region:",
        "ru": "☎️ Контакты координаторов по регионам:",
    },
    "coordinator_new_request_notification": {
        "uk": "🔔 Нове зголошення!\n\n👤 {name} ({link})\nПроєкт: {project} ({region})\nТип: {type}\nДати: {start} — {end}",
        "pl": "🔔 Nowe zgłoszenie!\n\n👤 {name} ({link})\nProjekt: {project} ({region})\nTyp: {type}\nDaty: {start} — {end}",
        "en": "🔔 New request!\n\n👤 {name} ({link})\nProject: {project} ({region})\nType: {type}\nDates: {start} — {end}",
        "ru": "🔔 Новая заявка!\n\n👤 {name} ({link})\nПроект: {project} ({region})\nТип: {type}\nДаты: {start} — {end}",
    },
    "btn_approve": {
        "uk": "✅ Підтвердити",
        "pl": "✅ Zatwierdź",
        "en": "✅ Approve",
        "ru": "✅ Подтвердить",
    },
    "btn_reject": {
        "uk": "❌ Відхилити",
        "pl": "❌ Odrzuć",
        "en": "❌ Reject",
        "ru": "❌ Отклонить",
    },
    "request_decided_worker": {
        "uk": "🔔 Ваше зголошення {status}.\nПроєкт: {project}\nДати: {start} — {end}",
        "pl": "🔔 Twoje zgłoszenie: {status}.\nProjekt: {project}\nDaty: {start} — {end}",
        "en": "🔔 Your request has been {status}.\nProject: {project}\nDates: {start} — {end}",
        "ru": "🔔 Ваша заявка: {status}.\nПроект: {project}\nДаты: {start} — {end}",
    },
    "coordinator_panel_title": {
        "uk": "🗂 Панель координатора. Оберіть фільтр:",
        "pl": "🗂 Panel koordynatora. Wybierz filtr:",
        "en": "🗂 Coordinator panel. Choose a filter:",
        "ru": "🗂 Панель координатора. Выберите фильтр:",
    },
    "filter_all": {"uk": "Усі", "pl": "Wszystkie", "en": "All", "ru": "Все"},
    "filter_new": {"uk": "Нові", "pl": "Nowe", "en": "New", "ru": "Новые"},
    "filter_processed": {
        "uk": "Опрацьовані",
        "pl": "Przetworzone",
        "en": "Processed",
        "ru": "Обработанные",
    },
    "l4_cannot_reject": {
        "uk": "⛔ Для лікарняного (L4) відхилення недоступне.",
        "pl": "⛔ Odrzucenie L4 jest niedostępne.",
        "en": "⛔ Sick leave (L4) cannot be rejected.",
        "ru": "⛔ Для больничного (L4) отклонение недоступно.",
    },
    "already_decided": {
        "uk": "Це зголошення вже опрацьовано.",
        "pl": "To zgłoszenie zostało już przetworzone.",
        "en": "This request has already been processed.",
        "ru": "Эта заявка уже обработана.",
    },
    "decision_saved": {
        "uk": "Рішення збережено.",
        "pl": "Decyzja zapisana.",
        "en": "Decision saved.",
        "ru": "Решение сохранено.",
    },
    "generic_error": {
        "uk": "⚠️ Сталася помилка. Спробуйте пізніше.",
        "pl": "⚠️ Wystąpił błąd. Spróbuj ponownie później.",
        "en": "⚠️ An error occurred. Please try again later.",
        "ru": "⚠️ Произошла ошибка. Попробуйте позже.",
    },
}


def t(key: str, lang: str, **kwargs) -> str:
    entry = TEXTS.get(key)
    if not entry:
        return key
    text = entry.get(lang) or entry.get("uk") or next(iter(entry.values()))
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
