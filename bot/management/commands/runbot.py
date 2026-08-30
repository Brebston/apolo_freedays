import asyncio

from django.core.management.base import BaseCommand


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
        asyncio.run(dp.start_polling(bot))
