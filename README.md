# apolo_freedays

Telegram bot and Django Admin for tracking employee absences at a Polish staffing agency: submitting, moderating, and automatically notifying about days off and sick leave (L4).

**Stack:** Python 3.12 · Django 5 · aiogram 3.x · PostgreSQL · Celery + Redis · Docker Compose

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Features](#features)
- [Quick Start (Docker)](#quick-start-docker)
- [Local Setup (without Docker)](#local-setup-without-docker)
- [Environment Variables](#environment-variables)
- [Django Admin — Entities](#django-admin--entities)
- [Custom Function Reference](#custom-function-reference)
- [Bot Business Logic (Flow)](#bot-business-logic-flow)
- [Bot Access Control](#bot-access-control)
- [Day-Off Limits](#day-off-limits)
- [Email Notifications](#email-notifications)
- [Localization](#localization)
- [Security](#security)
- [Development (Hot Reload)](#development-hot-reload)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)

---

## Overview

The system consists of two parts sharing a single PostgreSQL database:

1. **Telegram bot** (`aiogram 3.x`) — interface for workers (submitting requests) and coordinators (moderation).
2. **Django Admin** — web panel for the super admin: managing regions, projects, limits, user access, and email recipients.

The bot talks to the Django ORM directly (wrapped in `sync_to_async`), with no separate REST API — both components live in the same Django project and share the same models.

**Important:** there is no self-service registration in the bot. Access is granted exclusively by an administrator through Django Admin, based on Telegram ID.

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  Telegram   │◄────►│bot (aiogram) │      │web (gunicorn)│
│  API        │      │long polling  │      │Django Admin  │
└─────────────┘      └──────┬───────┘      └──────┬──────┘
                            │  Django ORM (sync_to_async) 
                            ▼                     ▼
                      ┌─────────────────────────────────────┐
                      │           PostgreSQL (db)           │
                      └─────────────────────────────────────┘
                             ▲
                             │ .delay()
                      ┌──────┴───────┐       ┌─────────────┐
                      │celery worker │◄────► │Redis (broker)│
                      │email tasks   │       └─────────────┘
                      └──────────────┘
```

Services in `docker-compose.yml`: `db`, `redis`, `migrate` (one-shot, generates and applies migrations before the rest start), `web`, `bot`, `celery`. Startup order is controlled via `depends_on: condition: service_healthy / service_completed_successfully`.

## Project Structure

```
config/                     Django settings, celery.py, urls.py, wsgi.py
users/
  models.py                 Custom User model (AbstractUser + telegram_id, language)
  forms.py                  Custom Django Admin user-creation form
                             (no username field, password optional)
  admin.py                  UserAdmin
core/
  models.py                 Region, Project, ProjectDateLimit, ProjectEmailRecipient, AbsenceRequest
  admin.py                  Django Admin for all project entities
  tasks.py                  Celery task for email notifications (HTML, Polish)
  templates/core/emails/    HTML email template
bot/
  loader.py                 Bot and Dispatcher instances (aiogram)
  states.py                 FSM states for submitting a request
  locales.py                Translation dictionary + t() function
  filters.py                Custom aiogram filter TextIs
  utils.py                  All Django ORM access from the bot (sync_to_async wrappers)
  keyboards/
    menus.py                Reply/inline keyboards for the main menu, type/region/project selection
    calendar.py             Interactive localized date-selection calendar
    inline.py                Coordinator decision, panel, and access-denied keyboards
  handlers/
    start.py                /start, language selection, Telegram-ID access check
    request_flow.py         Submitting a request (type → region → project → dates → confirmation)
    cabinet.py               Worker's cabinet (my requests, coordinator contacts)
    coordinator.py          Coordinator panel, request decisions
  management/commands/
    runbot.py                Django management command: starts aiogram polling
```

## Features

**Core (per the spec):**
- Multilingual — Ukrainian, Polish, English, Russian
- Submitting a request: type (day off / L4) → region → project → interactive calendar
- Past dates cannot be selected
- Confirmation card before submitting
- Push notification to the coordinator with inline "Approve/Reject" buttons directly in the message
- Coordinator panel: request history for their projects with filters (All/New/Processed)
- Rejection is forcibly disabled for L4
- Push notification to the worker about the decision
- Asynchronous email notifications via Celery to the To/CC recipients configured in Django Admin

**Added beyond the base spec:**
- **Telegram-ID-only access** — no in-bot registration or login at all; an administrator adds each user through Django Admin, entering just their Telegram ID (first/last name are required; email/phone/password are not)
- **Flexible access revocation via `is_active`** — access can be disabled with a single click without deleting the user or losing their request history
- **"Get my Telegram ID" button** on access denial — instantly produces a ready-to-forward text template for the coordinator
- **Monthly day-off limit per project** — total days off a worker can take per project within a calendar month, not just per single request
- **Worker limit per date** — how many people can be off at the same time on a given day, configured per project
- **Per-date limit override** (`ProjectDateLimit`) — e.g., Aug 5 → 2 people, Aug 6 → 5 people, falling back to the project's general limit
- **Polish HTML email** with a colored status badge instead of plain text
- **Automatic Django Admin logout** after 10 minutes of inactivity
- **WhiteNoise** for serving admin static files without a separate nginx
- **Health checks + a one-shot migrate service** in Docker Compose, eliminating the startup race condition

## Quick Start (Docker)

```bash
cp .env.example .env
# fill in BOT_TOKEN, POSTGRES_*, EMAIL_* (see "Environment Variables" below)

docker compose up --build
docker compose exec web python manage.py createsuperuser
```

Django Admin: http://localhost:8000/admin/
Bot: message it `/start` on Telegram — until your Telegram ID is added in Django Admin, the bot will show an access-denied message.

Startup order is fully automatic: `db`/`redis` become healthy, `migrate` generates and applies migrations, then `web`/`bot`/`celery` start.

## Local Setup (without Docker)

Requires: Python 3.12, PostgreSQL, Redis.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # POSTGRES_HOST=localhost, REDIS_URL=redis://localhost:6379/0

python manage.py migrate
python manage.py createsuperuser

# three separate terminals:
python manage.py runserver
python manage.py runbot
celery -A config worker -l info
```

## Environment Variables

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret key (unique in production) |
| `DJANGO_DEBUG` | `1` for development, `0` for production |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts |
| `POSTGRES_DB/USER/PASSWORD/HOST/PORT` | PostgreSQL connection (`HOST=db` in Docker) |
| `REDIS_URL` | Celery broker/backend |
| `BOT_TOKEN` | Token from [@BotFather](https://t.me/BotFather) |
| `EMAIL_HOST/PORT/HOST_USER/HOST_PASSWORD/USE_TLS` | SMTP (for Gmail — an App Password is required, not the regular account password) |
| `DEFAULT_FROM_EMAIL` | Sender address |

## Django Admin — Entities

| Model | Purpose |
|---|---|
| **Users** | First/last name (Latin letters), **Telegram ID** (the key field — without it the bot stays inaccessible), `is_active` = bot access, `is_staff` = coordinator. Email, phone, and password are optional (password is only needed for coordinators who log into Django Admin itself) |
| **Regions** | Region directory (Warsaw, Gdańsk, etc.) |
| **Projects** | Name, region, `dayoff_limit` (monthly day limit), `max_workers_per_day` (limit per date, empty = unlimited), `coordinators` (M2M), inline lists of email recipients and per-date limit overrides |
| **ProjectDateLimit** | Worker-limit override for a specific date of a specific project |
| **ProjectEmailRecipient** | Project's email recipients with a To/CC type |
| **AbsenceRequest** | Log of all requests, filterable by status/type/project/date |

## Custom Function Reference

### `bot/utils.py` — all Django ORM access from the bot

| Function | Description |
|---|---|
| `get_user_by_telegram_id(telegram_id)` | A "raw" lookup by Telegram ID (regardless of `is_active`) — used where the handler itself needs to branch on missing access (e.g. `/start`) |
| `get_active_user_by_telegram_id(telegram_id)` | Same, but only returns the user if `is_active=True` — used in every handler that grants access to actual bot functionality (submitting requests, the cabinet, the coordinator panel) |
| `set_user_language(telegram_id, language)` | Changes the user's interface language |
| `get_regions()` | List of all regions |
| `get_projects_by_region(region_id)` | Projects for a specific region |
| `get_project(project_id)` | A project with its region preloaded |
| `get_project_coordinators(project_id)` | Coordinators (`is_staff=True`, with a linked `telegram_id`) of a specific project |
| `get_coordinators_by_region(region_id)` | All coordinators of projects in a region (for the "Contacts" section) |
| `get_coordinator_project_ids(user_id)` | IDs of projects a coordinator is assigned to |
| `create_absence_request(user_id, project_id, request_type, dates)` | Creates an `AbsenceRequest`, storing the full list of dates in the `dates` field (not just start/end) |
| `get_used_dayoff_days_in_month(user_id, project_id, year, month, exclude_request_id=None)` | How many days off the worker has already used for the project in a calendar month (across all requests, excluding rejected ones) — the basis of the **monthly limit** |
| `get_workers_count_on_date(project_id, iso_date)` | How many UNIQUE project workers already have a day off on a specific date — the basis of the **per-date limit** |
| `get_date_capacity_limit(project_id, iso_date)` | Returns the overridden limit from `ProjectDateLimit` for the date, or `None` if no override exists (in which case the project's general limit applies) |
| `get_request(request_id)` | A request with user/project/region preloaded |
| `decide_request(request_id, status, decided_by_id)` | Atomically changes the status (only if it's still `pending`), returns `(request, changed: bool)` |
| `get_my_requests(user_id)` | The worker's last 20 requests |
| `get_project_requests(project_ids, status_filter)` | Requests for a coordinator's projects with an "All/New/Processed" filter |
| `save_notification_message_id(request_id, coordinator_telegram_id, message_id)` | Stores the sent push notification's message ID (for potential later editing) |

### `users/forms.py`

| Object | Description |
|---|---|
| `UserCreationForm` | Custom Django Admin user-creation form. The `username` field is removed from the form (auto-generated in `User.save()`); the password is fully optional — if left blank, `set_unusable_password()` is called (blocks Django Admin login, has no effect on bot access) |

### `bot/locales.py`

| Object | Description |
|---|---|
| `TEXTS` | Dictionary `{key: {uk, pl, en, ru}}` with all interface text |
| `t(key, lang, **kwargs)` | Returns the localized text; substitutes `{placeholders}`; falls back to Ukrainian if the language is missing |

### `bot/filters.py`

| Class | Description |
|---|---|
| `TextIs(key)` | Custom `aiogram.filters.BaseFilter` — compares the incoming message text with the localized button label for the current user's language (looked up from the DB by `telegram_id`) |

### `bot/keyboards/calendar.py`

| Function | Description |
|---|---|
| `build_calendar(year, month, selected, lang="uk")` | Generates the inline calendar: localized month name and weekday labels (uk/pl/en/ru), unclickable past dates, multi-select with a ✅ mark, month navigation, a "Selected: N" counter |

### `bot/keyboards/menus.py` / `bot/keyboards/inline.py`

| Function | Description |
|---|---|
| `language_keyboard()` | Language selection (4 buttons) — the first step on every `/start` |
| `main_menu_keyboard(lang, is_staff)` | Main reply menu; "Coordinator panel" button only shown if `is_staff=True` |
| `no_access_reply_keyboard(lang)` | A reduced reply menu for users without access — only the "🌐 Language" button |
| `request_type_keyboard(lang)` | "Day off" / "Sick leave (L4)" / "Cancel" |
| `regions_keyboard(regions)` / `projects_keyboard(projects)` | Dynamic lists sourced from the DB |
| `confirm_keyboard(lang)` | "Confirm" / "Cancel" |
| `decision_keyboard(request_id, lang, can_reject=True)` | Coordinator decision buttons; the "Reject" button is omitted if `can_reject=False` (L4) |
| `coordinator_panel_keyboard(lang)` | "All/New/Processed" filters |
| `requests_list_keyboard(requests)` | Request list for the coordinator panel |
| `no_access_keyboard(lang)` | An inline "🆔 Get my Telegram ID" button shown on access denial |

### `core/tasks.py`

| Object | Description |
|---|---|
| `send_absence_request_email(self, request_id)` | Celery task (bind=True, up to 3 retries): renders the HTML template in Polish, builds a plain-text fallback, sends to all of the project's To/CC recipients |
| `_STATUS_LABELS_PL`, `_TYPE_LABELS_PL` | Status/type → Polish label + badge color maps (independent of the DB's stored language — the email is always in Polish) |

### `core/models.py`

| Method/Object | Description |
|---|---|
| `latin_name_validator` | A `RegexValidator` allowing only `[A-Za-z\-]` for first/last names |
| `AbsenceRequest.can_be_rejected()` | `True` only for the "Day off" type; always `False` for L4 |
| `Project.dayoff_limit` | Monthly day-off limit (not a per-request limit) |
| `Project.max_workers_per_day` | `null=True` → unlimited; otherwise the general concurrent-absence limit per date |
| `AbsenceRequest.dates` | A `JSONField` holding the full list of selected ISO dates — needed for accurate monthly-limit counting with non-contiguous date selections |

### `users/models.py`

| Method | Description |
|---|---|
| `User.save()` | If `username` is empty, generates one automatically: email → `tg{telegram_id}` → a random string (in that priority order) |

## Bot Business Logic (Flow)

1. **`/start`** (and the "🌐 Language" button) → **always** shows language selection first, regardless of whether the user already has access
2. **Access check** immediately after the language is chosen: a lookup by `telegram_id`
   - **Found + `is_active=True`** → the language is saved to the DB, the main menu is shown
   - **Not found OR `is_active=False`** → an "access denied" message with an inline "🆔 Get my Telegram ID" button, and the reply menu is reduced to just the "🌐 Language" button
3. **"Get my Telegram ID"** → the bot sends a ready-to-forward text template containing the user's ID — just forward it to the coordinator
4. **Granting access**: an administrator/coordinator goes to **Django Admin → Users → Add user**, enters the Telegram ID (and first/last name) — that's enough, everything else is optional
5. **Submitting a request**: type → region → project (limits are read here) → calendar (every date tap checks the monthly limit and the per-date limit/override) → confirmation card → `create_absence_request()` → email + push to all of the project's coordinators with inline decision buttons
6. **Coordinator decision**: works identically whether triggered from the push notification or the coordinator panel; for L4 the "Reject" button is missing at the keyboard level and additionally blocked at the handler level

## Bot Access Control

There's no registration or login in the bot — access is fully controlled by an administrator:

1. A new worker messages the bot `/start`, picks a language, and receives an access-denied message with a button to get their Telegram ID
2. They forward that message to a coordinator/admin
3. The admin goes to Django Admin → Users → Add user, enters the Telegram ID, first name, and last name (email/phone/password can be left blank)
4. The worker sends `/start` again — they now see the main menu

**Revoking access** without deleting the user or losing their request history — just uncheck `is_active` in Django Admin. This is checked in every key bot handler via `get_active_user_by_telegram_id()`, not only on `/start`.

## Day-Off Limits

Priority order when selecting a date in the calendar (day-off type only):

1. **Monthly limit** (`Project.dayoff_limit`) — the sum of already-used days plus the days selected in the current session, within the same calendar month, cannot exceed the limit
2. **Per-date limit** — first checks `ProjectDateLimit` (an override for that specific date); if no entry exists, the general `Project.max_workers_per_day` applies; if that's also empty, there's no limit

## Email Notifications

Template: `core/templates/core/emails/new_absence_request.html` — an HTML table layout with inline styles (for email client compatibility), a colored status badge (yellow/green/red), always in Polish regardless of the language stored in the DB. `EmailMultiAlternatives.attach_alternative(html_body, "text/html")` — the email has both an HTML version and a plain-text fallback.

## Localization

Supported languages: `uk`, `pl`, `en`, `ru`. To add a new language — add a key to every entry in the `TEXTS` dictionary (`bot/locales.py`), to `_WEEKDAYS`/`_MONTHS` (`bot/keyboards/calendar.py`), and to the language selection keyboard (`bot/keyboards/menus.py:language_keyboard()`).

## Security

- **Whitelist access by Telegram ID** — no self-service registration in the bot whatsoever; anyone not added by an admin sees nothing beyond language selection
- `is_active` allows instantly revoking bot access without deleting the user (request history is preserved)
- The Django Admin password is optional when creating a user; if left blank, the account gets an `unusable password` (blocks Django Admin login, has no effect on the bot)
- Django Admin: automatic logout after 10 minutes of inactivity (`SESSION_COOKIE_AGE=600`, `SESSION_SAVE_EVERY_REQUEST=True`)
- Full names accept Latin letters only — guards against special-character injection in reports/emails
- SMTP via Gmail requires an App Password (2FA), not the regular account password

## Development (Hot Reload)

For local development with PyCharm, you can enable auto-restart on file save (without rebuilding the image) — `gunicorn --reload` for `web` and `watchmedo auto-restart` (the `watchdog` package) for `bot`/`celery`. **Development only** — remove these flags before a production release for the sake of stability under load.

## Troubleshooting

| Symptom | Cause / Fix |
|---|---|
| `Connection refused` to `db` on startup | Postgres isn't ready yet — resolved via a healthcheck plus the `migrate` service in `docker-compose.yml` |
| `Dependency on app with no migrations` | Migrations haven't been generated — the `migrate` service runs `makemigrations` + `migrate` before the other services start |
| Admin panel has no styling (CSS) | Gunicorn doesn't serve static files — resolved with WhiteNoise (`whitenoise.middleware.WhiteNoiseMiddleware`) |
| `WORKER TIMEOUT` in gunicorn | A single sync worker with too short a timeout — fixed with `--workers 2 --timeout 60` |
| A bot button just spins with no response | An unhandled exception in the handler — aiogram never calls `callback.answer()`; check `docker compose logs -f bot` at the moment of the click |
| `SMTPAuthenticationError 535` (Gmail) | An App Password (2FA) is required, not the regular password; run `docker compose up -d --force-recreate` after changing `.env`, since `restart` doesn't reload environment variables |
| A blocked user still sees the old menu | Telegram's reply keyboard doesn't refresh on its own — a new message with a new `reply_markup` must be sent (implemented in `bot/handlers/start.py`) |

## Roadmap

- `RedisStorage` for FSM instead of `MemoryStorage` (needed for multiple bot replicas)
- Pagination for the request list in the coordinator panel (currently capped at 30 records)
- Rate-limiting / anti-flood middleware for aiogram
- Bulk Telegram ID import (e.g. from CSV) for quickly seeding the initial user list
