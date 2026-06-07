from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .constants import PEOPLE, WEEKLY_TASKS


def bind_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=person.name, callback_data=f"bind:{person.id}")]
        for person in PEOPLE
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_keyboard(is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Очередь на 3 недели", callback_data="queue3")],
        [InlineKeyboardButton(text="Утро на 7 дней", callback_data="morning7")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text="Админ-панель", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Очередь туалета", callback_data="admin:menu:toilet")],
            [InlineKeyboardButton(text="Очередь спальника, суббота", callback_data="admin:menu:dorm_weekly")],
            [InlineKeyboardButton(text="Очередь спальника, утро", callback_data="admin:menu:morning")],
            [InlineKeyboardButton(text="Очередь на 3 недели", callback_data="queue3")],
        ]
    )


def weekly_admin_keyboard(task_id: str) -> InlineKeyboardMarkup:
    short = WEEKLY_TASKS[task_id]["short"]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"Старт круга: {short}", callback_data=f"admin:set_anchor:{task_id}"),
            ],
            [
                InlineKeyboardButton(text="Заменить назначенного", callback_data=f"admin:replace:{task_id}"),
            ],
            [
                InlineKeyboardButton(text="+ человек на усиленную уборку", callback_data=f"admin:add:{task_id}"),
            ],
            [
                InlineKeyboardButton(text="Уборки не было", callback_data=f"admin:skip_weekly:{task_id}"),
            ],
            [InlineKeyboardButton(text="Назад", callback_data="admin")],
        ]
    )


def morning_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Утра не было", callback_data="admin:skip_morning"),
                InlineKeyboardButton(text="Круг утра заново", callback_data="admin:restart_morning"),
            ],
            [InlineKeyboardButton(text="Утро на 7 дней", callback_data="morning7")],
            [InlineKeyboardButton(text="Назад", callback_data="admin")],
        ]
    )


def weekly_cant_keyboard(task_id: str, work_date: str, person_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Я не смогу по уважительной причине",
                    callback_data=f"cant_weekly:{task_id}:{work_date}:{person_id}",
                )
            ]
        ]
    )


def morning_cant_keyboard(work_date: str, person_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Я не смогу, взять взаймы",
                    callback_data=f"cant_morning:{work_date}:{person_id}",
                )
            ]
        ]
    )


def lender_cant_keyboard(debt_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Я не могу", callback_data=f"lender_cant:{debt_id}")]
        ]
    )


def absence_admin_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Заменить", callback_data=f"absence_replace:{request_id}"),
                InlineKeyboardButton(text="Оставить", callback_data=f"absence_keep:{request_id}"),
            ]
        ]
    )


def morning_manual_keyboard(debt_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ввести замену", callback_data=f"morning_manual:{debt_id}")]
        ]
    )


def task_title(task_id: str) -> str:
    return WEEKLY_TASKS[task_id]["title"]

