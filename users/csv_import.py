"""
Розбір CSV для масового імпорту працівників: ім'я, прізвище, телефон, Telegram ID.

Не залежить від Django — перевірки в базі (хто вже існує) робить адмінка.
Враховує реальні файли з Excel: роздільник «;» (польська локаль), UTF-8 з BOM,
Windows-1250/1251, Telegram ID у вигляді «359641501.0» або «3.59641501E+08».
"""

import csv
import io
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

NAME_RE = re.compile(r"^[A-Za-z\-]+$")  # те саме правило, що latin_name_validator у моделі
MAX_TELEGRAM_ID = 2**63 - 1
MAX_ROWS = 2000

HEADER_ALIASES = {
    "first_name": {"first_name", "firstname", "first name", "name", "imię", "imie", "ім'я", "імя", "ім’я", "имя"},
    "last_name": {"last_name", "lastname", "last name", "surname", "nazwisko", "прізвище", "фамилия"},
    "phone": {"phone", "phone_number", "telephone", "tel", "telefon", "numer telefonu", "телефон", "номер телефону", "номер телефона"},
    "telegram_id": {"telegram_id", "telegram id", "telegram", "tg", "tg_id", "tg id", "id telegram", "телеграм", "telegram-id"},
}
DEFAULT_ORDER = ["first_name", "last_name", "phone", "telegram_id"]


@dataclass
class ParsedRow:
    line: int
    first_name: str = ""
    last_name: str = ""
    phone: str = ""
    telegram_id: int | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


POLISH_LETTERS = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")


def _plausibility(text: str, encoding: str) -> int:
    """Скільки не-ASCII символів виглядають як справжні літери цієї мови."""
    if encoding == "cp1251":
        # Справжній кириличний текст — це цілі кириличні слова. Польський текст,
        # прочитаний як cp1251, дає поодинокі кириличні літери посеред латиниці.
        cyrillic = [("\u0400" <= ch <= "\u04ff") for ch in text]
        return sum(
            1 for i, is_cyr in enumerate(cyrillic)
            if is_cyr and ((i > 0 and cyrillic[i - 1]) or (i + 1 < len(cyrillic) and cyrillic[i + 1]))
        )
    return sum(1 for ch in text if ch in POLISH_LETTERS)


def decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    # Windows-1250 (польська) і Windows-1251 (кирилиця) — однобайтові, тож обидві
    # «успішно» декодують будь-що. Обираємо ту, що дає справжні літери.
    candidates = {}
    for encoding in ("cp1250", "cp1251"):  # за нічиєї перемагає перша (агенція польська)
        try:
            candidates[encoding] = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    if not candidates:
        return raw.decode("utf-8", errors="replace")
    best = max(candidates, key=lambda enc: _plausibility(candidates[enc], enc))
    return candidates[best]


def _detect_delimiter(text: str) -> str:
    sample = "\n".join(text.splitlines()[:10])
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
    except csv.Error:
        counts = {d: sample.count(d) for d in (";", ",", "\t")}
        return max(counts, key=counts.get)


def _header_mapping(row: list[str]) -> dict[str, int] | None:
    normalized = [cell.strip().lower() for cell in row]
    mapping = {}
    for key, aliases in HEADER_ALIASES.items():
        for index, cell in enumerate(normalized):
            if cell in aliases:
                mapping[key] = index
                break
    return mapping if len(mapping) >= 2 else None


def parse_telegram_id(value: str) -> int | None:
    cleaned = value.strip().replace(" ", "").replace("\u00a0", "").replace(",", ".")
    if not cleaned:
        return None
    try:
        number = Decimal(cleaned)
    except InvalidOperation:
        return None
    if number != number.to_integral_value() or number <= 0 or number > MAX_TELEGRAM_ID:
        return None
    return int(number)


def normalize_phone(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    prefix = "+" if value.startswith("+") else ""
    digits = re.sub(r"\D", "", value)
    if value.startswith("00"):
        prefix, digits = "+", digits[2:]
    return prefix + digits


def parse_csv(raw: bytes) -> tuple[list[ParsedRow], list[str]]:
    """Повертає (рядки з помилками чи без, загальні помилки файлу)."""
    text = decode(raw)
    if not text.strip():
        return [], ["The file is empty."]

    reader = csv.reader(io.StringIO(text), delimiter=_detect_delimiter(text))
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return [], ["The file has no data rows."]

    mapping = _header_mapping(rows[0])
    start_line = 2 if mapping else 1
    data_rows = rows[1:] if mapping else rows
    if mapping is None:
        mapping = {key: index for index, key in enumerate(DEFAULT_ORDER)}
    if len(data_rows) > MAX_ROWS:
        return [], [f"Too many rows: {len(data_rows)}. The limit is {MAX_ROWS} per file."]

    def cell(row, key):
        index = mapping.get(key)
        return row[index].strip() if index is not None and index < len(row) else ""

    parsed, seen_ids = [], {}
    for offset, row in enumerate(data_rows):
        item = ParsedRow(line=start_line + offset)
        item.first_name = cell(row, "first_name")
        item.last_name = cell(row, "last_name")
        item.phone = normalize_phone(cell(row, "phone"))
        raw_id = cell(row, "telegram_id")
        item.telegram_id = parse_telegram_id(raw_id)

        for key, label in (("first_name", "First name"), ("last_name", "Last name")):
            value = getattr(item, key)
            if not value:
                item.errors.append(f"{label} is empty.")
            elif not NAME_RE.match(value):
                item.errors.append(f"{label} “{value}” must use Latin letters and hyphens only (no spaces, digits or diacritics).")
        if item.telegram_id is None:
            item.errors.append(f"Telegram ID “{raw_id}” is not a valid number." if raw_id else "Telegram ID is empty.")
        elif item.telegram_id in seen_ids:
            item.errors.append(f"Duplicate Telegram ID — already on line {seen_ids[item.telegram_id]}.")
        else:
            seen_ids[item.telegram_id] = item.line
        if len(item.phone) > 32:
            item.errors.append("Phone number is longer than 32 characters.")
        parsed.append(item)

    return parsed, []


TEMPLATE_CSV = "first_name;last_name;phone;telegram_id\nOksana;Shevchenko;+48511222333;359641501\n"
