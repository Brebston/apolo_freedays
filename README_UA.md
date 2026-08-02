# apolo_freedays

Telegram-бот та Django Admin для обліку відсутностей працівників польської агенції праці: подання, модерація й автоматичне сповіщення про вихідні дні та лікарняні (L4).

**Стек:** Python 3.12 · Django 5 · aiogram 3.x · PostgreSQL · Celery + Redis · Docker Compose

---

## Зміст

- [Огляд](#огляд)
- [Архітектура](#архітектура)
- [Структура проєкту](#структура-проєкту)
- [Функціональні можливості](#функціональні-можливості)
- [Швидкий старт (Docker)](#швидкий-старт-docker)
- [Локальний запуск без Docker](#локальний-запуск-без-docker)
- [Змінні середовища](#змінні-середовища-env)
- [Django Admin — сутності](#django-admin--сутності)
- [Довідник кастомних функцій](#довідник-кастомних-функцій)
- [Бізнес-логіка бота (флоу)](#бізнес-логіка-бота-флоу)
- [Ліміти вихідних](#ліміти-вихідних)
- [Email-розсилка](#email-розсилка)
- [Локалізація](#локалізація)
- [Безпека](#безпека)
- [Розробка (hot-reload)](#розробка-hot-reload)
- [Усунення несправностей](#усунення-несправностей)
- [Дорожня карта](#дорожня-карта)

---

## Огляд

Система складається з двох частин, що працюють над спільною базою даних PostgreSQL:

1. **Telegram-бот** (`aiogram 3.x`) — інтерфейс для працівників (подача зголошень) і координаторів (модерація).
2. **Django Admin** — вебпанель для суперадміна: керування регіонами, проєктами, лімітами, координаторами та email-розсилками.

Бот звертається до Django ORM напряму (обгорнутий у `sync_to_async`), без окремого REST API — обидва компоненти живуть в одному Django-проєкті й діляться моделями.

## Архітектура

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  Telegram    │◄────►│  bot (aiogram) │      │ web (gunicorn)│
│  API         │      │  long polling  │      │ Django Admin  │
└─────────────┘      └──────┬───────┘      └──────┬──────┘
                             │  Django ORM (sync_to_async)  │
                             ▼                              ▼
                      ┌─────────────────────────────────────┐
                      │           PostgreSQL (db)             │
                      └─────────────────────────────────────┘
                             ▲
                             │ .delay()
                      ┌──────┴───────┐      ┌─────────────┐
                      │ celery worker │◄────►│ Redis (broker)│
                      │ email-таски   │      └─────────────┘
                      └──────────────┘
```

Сервіси в `docker-compose.yml`: `db`, `redis`, `migrate` (одноразовий, генерує й накатує міграції перед стартом решти), `web`, `bot`, `celery`. Порядок старту контролюється через `depends_on: condition: service_healthy / service_completed_successfully`.

## Структура проєкту

```
config/                     Django settings, celery.py, urls.py, wsgi.py
users/
  models.py                 Кастомна модель User (AbstractUser + telegram_id, мова)
  admin.py                  UserAdmin
core/
  models.py                 Region, Project, ProjectDateLimit, ProjectEmailRecipient, AbsenceRequest
  admin.py                  Django Admin для всіх сутностей проєкту
  tasks.py                  Celery-таска email-розсилки (HTML, польська)
  templates/core/emails/    HTML-шаблон листа
bot/
  loader.py                 Інстанси Bot і Dispatcher (aiogram)
  states.py                 FSM-стани (реєстрація, вхід, подання зголошення)
  locales.py                Словник перекладів + функція t()
  filters.py                Кастомний aiogram-фільтр TextIs
  utils.py                  Усі звернення до Django ORM (sync_to_async-обгортки)
  keyboards/
    menus.py                Reply/inline-клавіатури головного меню, вибору типу/регіону/проєкту
    calendar.py             Інтерактивний локалізований календар вибору дат
    inline.py                Клавіатури рішень координатора та панелі
  handlers/
    start.py                /start, вибір мови
    auth.py                 Реєстрація та вхід
    request_flow.py         Подання зголошення (тип → регіон → проєкт → дати → підтвердження)
    cabinet.py               Кабінет працівника (мої зголошення, контакти координаторів)
    coordinator.py          Панель координатора, рішення по зголошенню
  management/commands/
    runbot.py                Django management command: запуск aiogram polling
```

## Функціональні можливості

**Базові (за ТЗ):**
- Мультимовність — українська, польська, англійська, російська
- Реєстрація/вхід у боті (email + пароль), автовидалення повідомлення з паролем
- Подання зголошення: тип (вихідний/L4) → регіон → проєкт → інтерактивний календар
- Заборона вибору минулих дат
- Картка підтвердження перед відправкою
- Push-сповіщення координатору з inline-кнопками «Підтвердити/Відхилити» прямо в повідомленні
- Панель координатора: історія зголошень по своїх проєктах з фільтрами (Усі/Нові/Опрацьовані)
- Для L4 — відхилення примусово заблоковане
- Push-сповіщення працівнику про рішення
- Асинхронна email-розсилка через Celery на адресатів To/CC, налаштованих у Django Admin

**Додатково реалізовано понад базове ТЗ:**
- **Місячний ліміт вихідних на проєкт** — сумарна кількість вихідних працівника по проєкту за календарний місяць, а не лише за одне зголошення
- **Ліміт працівників на дату** — скільки людей одночасно можуть бути на вихідному в один день, окремо на проєкт
- **Перевизначення ліміту для конкретної дати** (`ProjectDateLimit`) — наприклад, 05.08 → 2 особи, 06.08 → 5 осіб, з фолбеком на загальний ліміт проєкту
- **HTML-лист польською мовою** з кольоровим статус-бейджем замість простого тексту
- **Автоматичне вилогування з Django Admin** за 10 хв неактивності
- **WhiteNoise** для роздачі статики адмінки без окремого nginx
- **Health check + одноразовий migrate-сервіс** у Docker Compose, що усуває гонитву умов при першому старті

## Швидкий старт (Docker)

```bash
cp .env.example .env
# заповніть BOT_TOKEN, POSTGRES_*, EMAIL_* (див. розділ "Змінні середовища")

docker compose up --build
docker compose exec web python manage.py createsuperuser
```

Django Admin: http://localhost:8000/admin/
Бот: напишіть йому `/start` у Telegram.

Порядок старту повністю автоматичний: `db`/`redis` → healthy, `migrate` генерує та накатує міграції, потім стартують `web`/`bot`/`celery`.

## Локальний запуск без Docker

Потрібні: Python 3.12, PostgreSQL, Redis.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # POSTGRES_HOST=localhost, REDIS_URL=redis://localhost:6379/0

python manage.py migrate
python manage.py createsuperuser

# три окремі термінали:
python manage.py runserver
python manage.py runbot
celery -A config worker -l info
```

## Змінні середовища (`.env`)

| Змінна | Призначення |
|---|---|
| `DJANGO_SECRET_KEY` | Секретний ключ Django (унікальний для продакшн) |
| `DJANGO_DEBUG` | `1` для розробки, `0` для продакшн |
| `DJANGO_ALLOWED_HOSTS` | Дозволені хости через кому |
| `POSTGRES_DB/USER/PASSWORD/HOST/PORT` | Підключення до PostgreSQL (`HOST=db` у Docker) |
| `REDIS_URL` | Брокер/бекенд Celery |
| `BOT_TOKEN` | Токен від [@BotFather](https://t.me/BotFather) |
| `EMAIL_HOST/PORT/HOST_USER/HOST_PASSWORD/USE_TLS` | SMTP (для Gmail — обов'язково App Password, не звичайний пароль) |
| `DEFAULT_FROM_EMAIL` | Адреса відправника |

## Django Admin — сутності

| Модель | Призначення |
|---|---|
| **Users** | ПІБ (латиниця), email, телефон, мова, `is_staff` = координатор, `Telegram ID` (заповнюється автоматично) |
| **Regions** | Довідник регіонів (Варшава, Гданськ тощо) |
| **Projects** | Назва, регіон, `dayoff_limit` (місячний ліміт днів), `max_workers_per_day` (ліміт на дату, порожньо = без обмежень), `coordinators` (M2M), inline-списки email-отримувачів і перевизначень лімітів на дату |
| **ProjectDateLimit** | Перевизначення ліміту працівників для конкретної дати конкретного проєкту |
| **ProjectEmailRecipient** | Email-адреси отримувачів проєкту з типом To/CC |
| **AbsenceRequest** | Журнал усіх зголошень з фільтрами за статусом/типом/проєктом/датою |

## Довідник кастомних функцій

### `bot/utils.py` — усі звернення до Django ORM з бота

| Функція | Опис |
|---|---|
| `is_valid_name(value)` | Перевіряє, що ім'я/прізвище містить лише латинські літери |
| `is_valid_email(value)` | Валідація формату email через Django-валідатор |
| `get_user_by_telegram_id(telegram_id)` | Пошук користувача за Telegram ID |
| `get_user_by_email(email)` | Пошук користувача за email (для входу/перевірки дублікатів при реєстрації) |
| `create_user(...)` | Створення нового User з хешуванням пароля |
| `link_telegram_and_check_password(email, password, telegram_id)` | Перевірка пароля при вході й прив'язка поточного Telegram-акаунта до існуючого User |
| `set_user_language(telegram_id, language)` | Зміна мови інтерфейсу користувача |
| `get_regions()` | Список усіх регіонів |
| `get_projects_by_region(region_id)` | Проєкти конкретного регіону |
| `get_project(project_id)` | Проєкт з підвантаженим регіоном |
| `get_project_coordinators(project_id)` | Координатори (`is_staff=True`, з прив'язаним `telegram_id`) конкретного проєкту |
| `get_coordinators_by_region(region_id)` | Усі координатори проєктів у регіоні (для розділу «Контакти») |
| `get_coordinator_project_ids(user_id)` | ID проєктів, за якими закріплений координатор |
| `create_absence_request(user_id, project_id, request_type, dates)` | Створює `AbsenceRequest`, зберігаючи повний список дат у полі `dates` (не лише start/end) |
| `get_used_dayoff_days_in_month(user_id, project_id, year, month, exclude_request_id=None)` | Скільки вихідних працівник уже використав по проєкту в календарному місяці (по всіх заявках, крім відхилених) — основа **місячного ліміту** |
| `get_workers_count_on_date(project_id, iso_date)` | Скільки УНІКАЛЬНИХ працівників проєкту вже мають вихідний на конкретну дату — основа **ліміту на дату** |
| `get_date_capacity_limit(project_id, iso_date)` | Повертає перевизначений ліміт з `ProjectDateLimit` для дати, або `None`, якщо перевизначення немає (тоді діє загальний ліміт проєкту) |
| `get_request(request_id)` | Зголошення з підвантаженими user/project/region |
| `decide_request(request_id, status, decided_by_id)` | Атомарно змінює статус (лише якщо він ще `pending`), повертає `(request, changed: bool)` |
| `get_my_requests(user_id)` | Останні 20 зголошень працівника |
| `get_project_requests(project_ids, status_filter)` | Зголошення по проєктах координатора з фільтром «Усі/Нові/Опрацьовані» |
| `save_notification_message_id(request_id, coordinator_telegram_id, message_id)` | Зберігає ID надісланого push-повідомлення (для можливого подальшого редагування) |

### `bot/locales.py`

| Об'єкт | Опис |
|---|---|
| `TEXTS` | Словник `{ключ: {uk, pl, en, ru}}` з усіма текстами інтерфейсу |
| `t(key, lang, **kwargs)` | Повертає локалізований текст; підставляє `{плейсхолдери}`; якщо мови немає — фолбек на українську |

### `bot/filters.py`

| Клас | Опис |
|---|---|
| `TextIs(key)` | Кастомний `aiogram.filters.BaseFilter` — порівнює текст вхідного повідомлення з локалізованою назвою кнопки для мови поточного користувача (визначається з БД за `telegram_id`) |

### `bot/keyboards/calendar.py`

| Функція | Опис |
|---|---|
| `build_calendar(year, month, selected, lang="uk")` | Генерує inline-календар: локалізовані назва місяця й дні тижня (uk/pl/en/ru), некликабельні минулі дати, мультивибір з позначкою ✅, навігація по місяцях, лічильник «Обрано: N» |

### `bot/keyboards/menus.py` / `bot/keyboards/inline.py`

| Функція | Опис |
|---|---|
| `language_keyboard()` | Вибір мови (4 кнопки) |
| `auth_keyboard(lang)` | «Реєстрація» / «Вхід» |
| `main_menu_keyboard(lang, is_staff)` | Головне reply-меню; кнопка «Панель координатора» лише якщо `is_staff=True` |
| `request_type_keyboard(lang)` | «Вихідний день» / «Лікарняний (L4)» / «Скасувати» |
| `regions_keyboard(regions)` / `projects_keyboard(projects)` | Динамічні списки з БД |
| `confirm_keyboard(lang)` | «Підтвердити» / «Скасувати» |
| `decision_keyboard(request_id, lang, can_reject=True)` | Кнопки рішення координатора; кнопка «Відхилити» відсутня, якщо `can_reject=False` (L4) |
| `coordinator_panel_keyboard(lang)` | Фільтри «Усі/Нові/Опрацьовані» |
| `requests_list_keyboard(requests)` | Список зголошень для панелі координатора |

### `core/tasks.py`

| Об'єкт | Опис |
|---|---|
| `send_absence_request_email(self, request_id)` | Celery-таска (bind=True, до 3 повторних спроб): рендерить HTML-шаблон польською, формує plain-text fallback, надсилає на всіх To/CC отримувачів проєкту |
| `_STATUS_LABELS_PL`, `_TYPE_LABELS_PL` | Мапи статус/тип → польська мітка + колір бейджа (незалежно від мови даних у БД — лист завжди польською) |

### `core/models.py`

| Метод/об'єкт | Опис |
|---|---|
| `latin_name_validator` | `RegexValidator`, дозволяє лише `[A-Za-z\-]` для імені/прізвища |
| `AbsenceRequest.can_be_rejected()` | `True` лише для типу «Вихідний»; для L4 завжди `False` — використовується і ботом, і потенційно адмінкою для примусового блокування відхилення |
| `Project.dayoff_limit` | Місячний ліміт вихідних (не ліміт на одне зголошення) |
| `Project.max_workers_per_day` | `null=True` → без обмежень; інакше — загальний ліміт одночасної відсутності по датах |
| `AbsenceRequest.dates` | `JSONField` з повним списком обраних ISO-дат — потрібен для точного підрахунку місячного ліміту при негрупових вибірках днів |

### `users/models.py`

| Метод | Опис |
|---|---|
| `User.save()` | Якщо `username` порожній — автоматично встановлює його рівним `email` (username не запитується окремо в боті) |

## Бізнес-логіка бота (флоу)

1. **`/start`** → якщо користувач невідомий — вибір мови → «Реєстрація»/«Вхід»; якщо відомий — одразу головне меню
2. **Реєстрація**: ім'я → прізвище (латиниця, валідація) → email (унікальність) → телефон → пароль → `create_user()` → повідомлення з паролем видаляється (`message.delete()`)
3. **Вхід**: email → пароль → `link_telegram_and_check_password()` прив'язує поточний `telegram_id` до існуючого акаунта (типовий сценарій для координатора, якого спершу створили в Django Admin)
4. **Подання зголошення**: тип → регіон → проєкт (тут-таки читаються ліміти: `dayoff_limit`, `max_workers_per_day`) → календар (кожен тап на дату перевіряє місячний ліміт і ліміт на дату/перевизначення) → картка підтвердження → `create_absence_request()` → `send_absence_request_email.delay()` + push усім координаторам проєкту з inline-кнопками рішення
5. **Рішення координатора**: спрацьовує однаково і з push-повідомлення, і з панелі координатора (`bot/handlers/coordinator.py:decide()`); для L4 кнопка «Відхилити» відсутня на рівні клавіатури й додатково заблокована на рівні хендлера

## Ліміти вихідних

Пріоритет при виборі дати в календарі (лише для типу «Вихідний»):

1. **Місячний ліміт** (`Project.dayoff_limit`) — сума вже використаних + обраних у поточній сесії днів у тому самому календарному місяці не може перевищити ліміт
2. **Ліміт на дату** — спочатку перевіряється `ProjectDateLimit` (перевизначення саме для цієї дати); якщо запису немає — використовується загальний `Project.max_workers_per_day`; якщо й він порожній — обмежень немає

## Email-розсилка

Шаблон: `core/templates/core/emails/new_absence_request.html` — HTML-таблична верстка з inline-стилями (для сумісності з поштовими клієнтами), кольоровий статус-бейдж (жовтий/зелений/червоний), польська мова незалежно від мови даних у БД. `EmailMultiAlternatives.attach_alternative(html_body, "text/html")` — лист має і HTML, і plain-text fallback.

## Локалізація

Підтримувані мови: `uk`, `pl`, `en`, `ru`. Щоб додати нову мову — додати ключ у кожен запис словника `TEXTS` (`bot/locales.py`), у `_WEEKDAYS`/`_MONTHS` (`bot/keyboards/calendar.py`) і в клавіатуру вибору мови (`bot/keyboards/menus.py:language_keyboard()`).

## Безпека

- Пароль ніколи не залишається в чаті — повідомлення з ним видаляється одразу після обробки
- Паролі зберігаються через `django.contrib.auth.hashers` (хешування, не plain-text)
- Django Admin: автоматичне вилогування за 10 хв неактивності (`SESSION_COOKIE_AGE=600`, `SESSION_SAVE_EVERY_REQUEST=True`)
- ПІБ приймається лише латиницею — захист від ін'єкцій спецсимволів у звітах/листах
- SMTP через Gmail вимагає App Password (2FA), а не звичайний пароль акаунта

## Розробка (hot-reload)

Для локальної розробки з PyCharm можна увімкнути автоперезапуск процесів при збереженні файлу (без ребілду образу) — `gunicorn --reload` для `web` і `watchmedo auto-restart` (пакет `watchdog`) для `bot`/`celery`. **Використовувати лише в розробці** — перед продакшн-релізом прибрати ці прапорці заради стабільності під навантаженням.

## Усунення несправностей

| Симптом | Причина / рішення |
|---|---|
| `Connection refused` до `db` при старті | Postgres ще не готовий — вирішено healthcheck + сервісом `migrate` у `docker-compose.yml` |
| `Dependency on app with no migrations` | Міграції не згенеровані — сервіс `migrate` виконує `makemigrations` + `migrate` перед стартом інших сервісів |
| Адмінка без стилів (CSS) | Gunicorn не роздає статику — вирішено WhiteNoise (`whitenoise.middleware.WhiteNoiseMiddleware`) |
| `WORKER TIMEOUT` у gunicorn | Один sync-воркер і замалий таймаут — `--workers 2 --timeout 60` |
| Кнопка в боті «крутиться» без відповіді | Необроблений exception у хендлері — aiogram не викликає `callback.answer()`; дивитись `docker compose logs -f bot` в момент кліку |
| `SMTPAuthenticationError 535` (Gmail) | Потрібен App Password (2FA), не звичайний пароль; `docker compose up -d --force-recreate` після зміни `.env`, бо `restart` не перечитує змінні |

## Дорожня карта

- `RedisStorage` для FSM замість `MemoryStorage` (потрібно для кількох реплік бота)
- Пагінація списку зголошень у панелі координатора (зараз ліміт 30 записів)
- Rate-limiting / anti-flood middleware для aiogram
- Автоматичне вилогування самого бота за неактивністю (окремо від Django Admin)