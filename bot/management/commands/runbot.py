import asyncio

from django.core.management.base import BaseCommand
from django.conf import settings

from aiogram.types import MenuButtonWebApp, WebAppInfo


class Command(BaseCommand):
    help = "Launching a Telegram bot (aiogram, long polling)"

    def handle(self, *args, **options):
        from bot.handlers import (
            cabinet,
            coordinator,
            request_flow,
            service_request_flow,
            start,
        )
        from bot.loader import bot, dp

        dp.include_router(start.router)
        dp.include_router(request_flow.router)
        dp.include_router(service_request_flow.router)
        dp.include_router(coordinator.router)
        dp.include_router(cabinet.router)

        self.stdout.write(self.style.SUCCESS("Bot started. Waiting for messages..."))

        async def set_menu_button(bot):
            if settings.WEBAPP_URL:
                await bot.set_chat_menu_button(
                    menu_button=MenuButtonWebApp(
                        text="Apolo", web_app=WebAppInfo(url=settings.WEBAPP_URL)
                    ),
                )

        dp.startup.register(set_menu_button)
        asyncio.run(dp.start_polling(bot))
