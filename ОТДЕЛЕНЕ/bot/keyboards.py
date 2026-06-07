from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .constants import MORNING_ROSTER, PEOPLE, PEOPLE_BY_ID, WEEKLY_TASKS


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
    rows = []
    if task_id == "toilet":
        rows.append(
            [
                InlineKeyboardButton(text=f"Старт круга: {short}", callback_data=f"admin:set_anchor:{task_id}"),
            ]
        )
    rows.extend(
        [
            [
                InlineKeyboardButton(text="Заменить назначенного", callback_data=f"admin:replace:{task_id}"),
            ],
            [
                InlineKeyboardButton(text="+ человек на усиленную уборку", callback_data=f"admin:add:{task_id}"),
            ],
            [
                InlineKeyboardButton(text="Уборки не было", callback_data=f"admin:skip_weekly:{task_id}"),
            ],
            [
                InlineKeyboardButton(text="Внести последнюю субботу", callback_data=f"admin:history_last:{task_id}"),
            ],
            [
                InlineKeyboardButton(text="История уборок", callback_data=f"admin:history_show:{task_id}"),
            ],
            [InlineKeyboardButton(text="Назад", callback_data="admin")],
        ]
    )
    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def morning_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Утра не было", callback_data="admin:skip_morning"),
                InlineKeyboardButton(text="Круг утра заново", callback_data="admin:restart_morning"),
            ],
            [InlineKeyboardButton(text="Показать уборщиков на завтра", callback_data="admin:morning_tomorrow")],
            [InlineKeyboardButton(text="Утро на 7 дней", callback_data="morning7")],
            [InlineKeyboardButton(text="Назад", callback_data="admin")],
        ]
    )


def people_keyboard(
    callback_prefix: str,
    person_ids: tuple[str, ...] | list[str],
    back_callback: str | None = None,
) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=PEOPLE_BY_ID[person_id].name, callback_data=f"{callback_prefix}:{person_id}")]
        for person_id in person_ids
    ]
    if back_callback:
        rows.append([InlineKeyboardButton(text="Назад", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def morning_pair_keyboard(work_date: str) -> InlineKeyboardMarkup:
    rows = []
    for index, first_id in enumerate(MORNING_ROSTER):
        second_id = MORNING_ROSTER[(index + 1) % len(MORNING_ROSTER)]
        first = PEOPLE_BY_ID[first_id].name
        second = PEOPLE_BY_ID[second_id].name
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{first} + {second}",
                    callback_data=f"admin:morning_pair:{work_date}:{first_id}:{second_id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="Назад", callback_data="admin:menu:morning")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def morning_tomorrow_keyboard(work_date: str, slots) -> InlineKeyboardMarkup:
    rows = []
    for slot in slots:
        person_name = PEOPLE_BY_ID[slot.person_id].name
        rows.append(
            [
                InlineKeyboardButton(text=person_name, callback_data="noop"),
                InlineKeyboardButton(
                    text="Заменить",
                    callback_data=f"admin:replace_morning_slot:{work_date}:{slot.slot_no}",
                ),
            ]
        )
    rows.append([InlineKeyboardButton(text="Назад", callback_data="admin:menu:morning")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


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

