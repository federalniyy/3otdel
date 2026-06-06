from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import load_config
from .handlers import create_router
from .notifications import notify_morning_for_tomorrow, notify_weekly_for_tomorrow
from .services import MorningService, WeeklyService
from .storage import JsonStore


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    if not config.bot_token:
        raise RuntimeError("BOT_TOKEN is empty. Create .env from .env.example.")

    store = JsonStore(config.data_path)
    store.set_admin_telegram_id(config.admin_telegram_id)
    weekly = WeeklyService(store)
    morning = MorningService(store)

    bot = Bot(config.bot_token)
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(create_router(store, weekly, morning))

    scheduler = AsyncIOScheduler(timezone=config.timezone)
    scheduler.add_job(
        notify_weekly_for_tomorrow,
        CronTrigger(day_of_week="fri", hour=18, minute=0, timezone=config.timezone),
        args=[store, weekly, bot, config.timezone],
        id="weekly_friday_notice",
        replace_existing=True,
    )
    scheduler.add_job(
        notify_morning_for_tomorrow,
        CronTrigger(hour=21, minute=0, timezone=config.timezone),
        args=[store, morning, bot, config.timezone],
        id="morning_21_notice",
        replace_existing=True,
    )
    scheduler.start()

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
