from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot

from .keyboards import lender_cant_keyboard, morning_cant_keyboard, morning_manual_keyboard, task_title, weekly_cant_keyboard
from .services import MorningService, WeeklyService
from .storage import JsonStore
from .utils import person_name


async def notify_admins(store: JsonStore, bot: Bot, text: str, reply_markup=None) -> None:
    for admin in store.admins():
        await bot.send_message(admin["chat_id"], text, reply_markup=reply_markup)


async def notify_weekly_for_tomorrow(
    store: JsonStore,
    weekly: WeeklyService,
    bot: Bot,
    timezone: str,
) -> None:
    today = datetime.now(ZoneInfo(timezone)).date()
    tomorrow = today + timedelta(days=1)
    for task_id in ("dorm_weekly", "toilet"):
        assignment = weekly.ensure_assignment(task_id, tomorrow)
        if assignment is None or assignment.status == "skipped":
            continue
        for person_id, weight in assignment.participants:
            people = store.people_with_chat([person_id])
            if not people:
                await notify_admins(
                    store,
                    bot,
                    f"Не могу уведомить {person_name(person_id)}: он не нажал /start.",
                )
                continue
            await bot.send_message(
                people[0]["chat_id"],
                f"Завтра {tomorrow.strftime('%d.%m.%Y')}: {task_title(task_id)}. Доля: {weight:g}.",
                reply_markup=weekly_cant_keyboard(task_id, tomorrow.isoformat(), person_id),
            )


async def notify_morning_for_tomorrow(
    store: JsonStore,
    morning: MorningService,
    bot: Bot,
    timezone: str,
) -> None:
    tomorrow = datetime.now(ZoneInfo(timezone)).date() + timedelta(days=1)
    slots = morning.ensure_day(tomorrow)
    if not slots:
        return
    for slot in slots:
        people = store.people_with_chat([slot.person_id])
        text = f"Завтра утром {tomorrow.strftime('%d.%m.%Y')} уборка спального помещения."
        if slot.person_id != slot.original_person_id:
            text += f" Ты идешь за {person_name(slot.original_person_id)}."
        if not people:
            await notify_admins(
                store,
                bot,
                f"Не могу уведомить {person_name(slot.person_id)}: он не нажал /start.",
            )
            continue
        await bot.send_message(
            people[0]["chat_id"],
            text,
            reply_markup=morning_cant_keyboard(tomorrow.isoformat(), slot.person_id),
        )


async def notify_lender(
    store: JsonStore,
    bot: Bot,
    work_date: date,
    borrower_id: str,
    lender_id: str,
    debt_id: int,
) -> None:
    people = store.people_with_chat([lender_id])
    text = (
        f"{person_name(borrower_id)} не может выйти утром {work_date.strftime('%d.%m.%Y')} "
        f"и берет у тебя взаймы. Если ты тоже не можешь, нажми кнопку."
    )
    if not people:
        await notify_admins(
            store,
            bot,
            f"{person_name(lender_id)} должен заменить {person_name(borrower_id)}, но он не нажал /start.",
            reply_markup=morning_manual_keyboard(debt_id),
        )
        return
    await bot.send_message(people[0]["chat_id"], text, reply_markup=lender_cant_keyboard(debt_id))
