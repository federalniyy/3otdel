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
            [
                InlineKeyboardButton(text="Старт круга спальник", callback_data="admin:set_anchor:dorm_weekly"),
                InlineKeyboardButton(text="Старт круга туалет", callback_data="admin:set_anchor:toilet"),
            ],
            [
                InlineKeyboardButton(text="Заменить спальник", callback_data="admin:replace:dorm_weekly"),
                InlineKeyboardButton(text="Заменить туалет", callback_data="admin:replace:toilet"),
            ],
            [
                InlineKeyboardButton(text="+ человек спальник", callback_data="admin:add:dorm_weekly"),
                InlineKeyboardButton(text="+ человек туалет", callback_data="admin:add:toilet"),
            ],
            [
                InlineKeyboardButton(text="Спальника не было", callback_data="admin:skip_weekly:dorm_weekly"),
                InlineKeyboardButton(text="Туалета не было", callback_data="admin:skip_weekly:toilet"),
            ],
            [
                InlineKeyboardButton(text="Утра не было", callback_data="admin:skip_morning"),
                InlineKeyboardButton(text="Круг утра заново", callback_data="admin:restart_morning"),
            ],
            [InlineKeyboardButton(text="Очередь на 3 недели", callback_data="queue3")],
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

