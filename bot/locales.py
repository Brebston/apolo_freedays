"""
Просте, залежне від ключа сховище перекладів.
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
    "welcome": {
        "uk": "Вітаємо! Оберіть дію:",
        "pl": "Witamy! Wybierz akcję:",
        "en": "Welcome! Choose an action:",
        "ru": "Добро пожаловать! Выберите действие:",
    },
    "btn_register": {"uk": "📝 Реєстрація", "pl": "📝 Rejestracja", "en": "📝 Register", "ru": "📝 Регистрация"},
    "btn_login": {"uk": "🔑 Вхід", "pl": "🔑 Logowanie", "en": "🔑 Login", "ru": "🔑 Вход"},

    "reg_ask_first_name": {
        "uk": "Введіть ваше ім'я (латинськими літерами, без цифр і символів):",
        "pl": "Podaj swoje imię (literami łacińskimi, bez cyfr i symboli):",
        "en": "Enter your first name (Latin letters only, no digits or symbols):",
        "ru": "Введите имя (латинскими буквами, без цифр и символов):",
    },
    "reg_invalid_name": {
        "uk": "❌ Дозволені лише латинські літери. Спробуйте ще раз:",
        "pl": "❌ Dozwolone są tylko litery łacińskie. Spróbuj ponownie:",
        "en": "❌ Only Latin letters are allowed. Try again:",
        "ru": "❌ Разрешены только латинские буквы. Попробуйте снова:",
    },
    "reg_ask_last_name": {
        "uk": "Введіть ваше прізвище:",
        "pl": "Podaj swoje nazwisko:",
        "en": "Enter your last name:",
        "ru": "Введите фамилию:",
    },
    "reg_ask_email": {
        "uk": "Введіть вашу email-адресу:",
        "pl": "Podaj swój adres email:",
        "en": "Enter your email address:",
        "ru": "Введите ваш email:",
    },
    "reg_invalid_email": {
        "uk": "❌ Некоректний формат email. Спробуйте ще раз:",
        "pl": "❌ Nieprawidłowy format email. Spróbuj ponownie:",
        "en": "❌ Invalid email format. Try again:",
        "ru": "❌ Некорректный формат email. Попробуйте снова:",
    },
    "reg_email_exists": {
        "uk": "❌ Користувач із такою поштою вже існує. Скористайтесь «Вхід» або введіть іншу пошту:",
        "pl": "❌ Użytkownik z tym adresem już istnieje. Użyj «Logowanie» albo podaj inny email:",
        "en": "❌ A user with this email already exists. Use \"Login\" or enter another email:",
        "ru": "❌ Пользователь с такой почтой уже существует. Используйте «Вход» или введите другую почту:",
    },
    "reg_ask_phone": {
        "uk": "Введіть ваш номер телефону:",
        "pl": "Podaj swój numer telefonu:",
        "en": "Enter your phone number:",
        "ru": "Введите номер телефона:",
    },
    "reg_ask_password": {
        "uk": "Придумайте пароль (це повідомлення буде видалено одразу після реєстрації):",
        "pl": "Ustaw hasło (ta wiadomość zostanie usunięta zaraz po rejestracji):",
        "en": "Set a password (this message will be deleted right after registration):",
        "ru": "Придумайте пароль (это сообщение будет удалено сразу после регистрации):",
    },
    "reg_success": {
        "uk": "✅ Реєстрацію завершено успішно!",
        "pl": "✅ Rejestracja zakończona pomyślnie!",
        "en": "✅ Registration completed successfully!",
        "ru": "✅ Регистрация успешно завершена!",
    },
    "login_ask_email": {
        "uk": "Введіть email вашого акаунта:",
        "pl": "Podaj email swojego konta:",
        "en": "Enter your account email:",
        "ru": "Введите email вашего аккаунта:",
    },
    "login_ask_password": {
        "uk": "Введіть пароль (це повідомлення буде видалено):",
        "pl": "Podaj hasło (ta wiadomość zostanie usunięta):",
        "en": "Enter your password (this message will be deleted):",
        "ru": "Введите пароль (это сообщение будет удалено):",
    },
    "login_failed": {
        "uk": "❌ Невірний email або пароль. Спробуйте /start ще раз.",
        "pl": "❌ Nieprawidłowy email lub hasło. Spróbuj ponownie /start.",
        "en": "❌ Invalid email or password. Try /start again.",
        "ru": "❌ Неверный email или пароль. Попробуйте /start снова.",
    },
    "login_success": {
        "uk": "✅ Вхід виконано успішно!",
        "pl": "✅ Zalogowano pomyślnie!",
        "en": "✅ Logged in successfully!",
        "ru": "✅ Вход выполнен успешно!",
    },

    "main_menu_title": {
        "uk": "Головне меню:",
        "pl": "Menu główne:",
        "en": "Main menu:",
        "ru": "Главное меню:",
    },
    "btn_new_request": {"uk": "➕ Подати зголошення", "pl": "➕ Nowe zgłoszenie", "en": "➕ New request", "ru": "➕ Подать заявку"},
    "btn_my_requests": {"uk": "📋 Мої зголошення", "pl": "📋 Moje zgłoszenia", "en": "📋 My requests", "ru": "📋 Мои заявки"},
    "btn_coordinators": {"uk": "☎️ Координатори", "pl": "☎️ Koordynatorzy", "en": "☎️ Coordinators", "ru": "☎️ Координаторы"},
    "btn_language": {"uk": "🌐 Мова", "pl": "🌐 Język", "en": "🌐 Language", "ru": "🌐 Язык"},
    "btn_coordinator_panel": {"uk": "🗂 Панель координатора", "pl": "🗂 Panel koordynatora", "en": "🗂 Coordinator panel", "ru": "🗂 Панель координатора"},
    "btn_cancel": {"uk": "❌ Скасувати", "pl": "❌ Anuluj", "en": "❌ Cancel", "ru": "❌ Отмена"},

    "choose_request_type": {
        "uk": "Оберіть тип зголошення:",
        "pl": "Wybierz typ zgłoszenia:",
        "en": "Choose the request type:",
        "ru": "Выберите тип заявки:",
    },
    "btn_dayoff": {"uk": "🏖 Вихідний день", "pl": "🏖 Dzień wolny", "en": "🏖 Day off", "ru": "🏖 Выходной день"},
    "btn_l4": {"uk": "🤒 Лікарняний (L4)", "pl": "🤒 Zwolnienie (L4)", "en": "🤒 Sick leave (L4)", "ru": "🤒 Больничный (L4)"},

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
    "confirm_request": {
        "uk": "Перевірте деталі зголошення:\n\nТип: {type}\nПроєкт: {project} ({region})\nДати: {start} — {end}\nКількість днів: {count}",
        "pl": "Sprawdź szczegóły zgłoszenia:\n\nTyp: {type}\nProjekt: {project} ({region})\nDaty: {start} — {end}\nLiczba dni: {count}",
        "en": "Please review the request details:\n\nType: {type}\nProject: {project} ({region})\nDates: {start} — {end}\nDays: {count}",
        "ru": "Проверьте детали заявки:\n\nТип: {type}\nПроект: {project} ({region})\nДаты: {start} — {end}\nКоличество дней: {count}",
    },
    "btn_confirm": {"uk": "✅ Підтвердити", "pl": "✅ Potwierdź", "en": "✅ Confirm", "ru": "✅ Подтвердить"},
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
    "status_pending": {"uk": "⏳ Очікує", "pl": "⏳ Oczekuje", "en": "⏳ Pending", "ru": "⏳ Ожидает"},
    "status_approved": {"uk": "✅ Підтверджено", "pl": "✅ Zatwierdzono", "en": "✅ Approved", "ru": "✅ Подтверждено"},
    "status_rejected": {"uk": "❌ Відхилено", "pl": "❌ Odrzucono", "en": "❌ Rejected", "ru": "❌ Отклонено"},

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
    "btn_approve": {"uk": "✅ Підтвердити", "pl": "✅ Zatwierdź", "en": "✅ Approve", "ru": "✅ Подтвердить"},
    "btn_reject": {"uk": "❌ Відхилити", "pl": "❌ Odrzuć", "en": "❌ Reject", "ru": "❌ Отклонить"},

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
    "filter_processed": {"uk": "Опрацьовані", "pl": "Przetworzone", "en": "Processed", "ru": "Обработанные"},

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
