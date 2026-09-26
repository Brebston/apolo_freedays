"""
Перевірка підпису Telegram Mini App initData.

Алгоритм з офіційної документації Telegram:
  secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token)
  data_check_string = відсортовані пари "key=value" (крім hash), через "\n"
  hash має дорівнювати hex(HMAC_SHA256(key=secret_key, msg=data_check_string))

Модуль не залежить від Django — його можна тестувати окремо.
"""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


class InitDataError(Exception):
    pass


def validate_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400, now: float | None = None) -> dict:
    """
    Повертає розібрані дані (з уже декодованим полем "user"), якщо підпис
    правильний і дані не застарілі. Інакше кидає InitDataError.
    """
    if not init_data:
        raise InitDataError("empty")
    if not bot_token:
        raise InitDataError("bot_token_missing")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("hash_missing")

    data_check_string = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise InitDataError("bad_signature")

    try:
        auth_date = int(pairs.get("auth_date", "0"))
    except ValueError as exc:
        raise InitDataError("bad_auth_date") from exc

    current = now if now is not None else time.time()
    if max_age_seconds and current - auth_date > max_age_seconds:
        raise InitDataError("expired")

    try:
        pairs["user"] = json.loads(pairs.get("user", "{}"))
    except json.JSONDecodeError as exc:
        raise InitDataError("bad_user") from exc

    if not isinstance(pairs["user"], dict) or "id" not in pairs["user"]:
        raise InitDataError("user_missing")

    return pairs
