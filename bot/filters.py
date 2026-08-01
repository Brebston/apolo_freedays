from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot.locales import t
from bot.utils import get_user_by_telegram_id


class TextIs(BaseFilter):
    """
    Порівнює текст повідомлення з локалізованою назвою кнопки для мови
    поточного користувача (мова визначається з БД за telegram_id).
    """

    def __init__(self, key: str):
        self.key = key

    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        user = await get_user_by_telegram_id(message.from_user.id)
        lang = user.language if user else "uk"
        return message.text == t(self.key, lang)
