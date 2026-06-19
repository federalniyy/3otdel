from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from bot.config import load_config
    from bot.handlers import create_router
    from bot.notifications import ask_weekly_done, notify_morning_for_tomorrow, notify_weekly_for_tomorrow
    from bot.services import MorningService, WeeklyService
    from bot.storage import JsonStore
else:
    from .config import load_config
    from .handlers import create_router
    from .notifications import ask_weekly_done, notify_morning_for_tomorrow, notify_weekly_for_tomorrow
    from .services import MorningService, WeeklyService
    from .storage import JsonStore


def complete_past_weekly(weekly: WeeklyService, timezone: str) -> None:
    today = datetime.now(ZoneInfo(timezone)).date()
    weekly.complete_past_planned(today)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    if not config.bot_token:
        raise RuntimeError("BOT_TOKEN is empty. Create .env from .env.example.")

    store = JsonStore(config.data_path)
    store.set_admin_telegram_id(config.admin_telegram_id)
    weekly = WeeklyService(store)
    morning = MorningService(store)
    complete_past_weekly(weekly, config.timezone)

    bot = Bot(config.bot_token)
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(create_router(store, weekly, morning, config.timezone))

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
    scheduler.add_job(
        ask_weekly_done,
        CronTrigger(day_of_week="sat", hour=20, minute=30, timezone=config.timezone),
        args=[store, weekly, bot, config.timezone],
        id="weekly_saturday_done_question",
        replace_existing=True,
    )
    scheduler.add_job(
        complete_past_weekly,
        CronTrigger(hour=0, minute=5, timezone=config.timezone),
        args=[weekly, config.timezone],
        id="complete_past_weekly",
        replace_existing=True,
    )
    scheduler.start()

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
