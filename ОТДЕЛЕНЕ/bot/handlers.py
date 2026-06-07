from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from .constants import WEEKLY_TASKS
from .keyboards import (
    absence_admin_keyboard,
    admin_keyboard,
    bind_keyboard,
    main_keyboard,
    morning_admin_keyboard,
    morning_manual_keyboard,
    task_title,
    weekly_admin_keyboard,
)
from .notifications import notify_admins, notify_lender
from .services import MorningService, WeeklyService
from .storage import JsonStore
from .utils import format_people, parse_date, parse_person, person_name


class Form(StatesGroup):
    set_anchor = State()
    replace_weekly = State()
    add_weekly = State()
    skip_weekly = State()
    skip_morning = State()
    restart_morning = State()
    weekly_absence_reason = State()
    weekly_absence_replacement = State()
    morning_debt_replacement = State()


def create_router(
    store: JsonStore,
    weekly: WeeklyService,
    morning: MorningService,
    timezone: str = "Europe/Moscow",
) -> Router:
    router = Router()

    def today() -> date:
        return datetime.now(ZoneInfo(timezone)).date()

    def bound_person(user_id: int) -> dict | None:
        return store.person_by_telegram(user_id)

    def is_admin(user_id: int) -> bool:
        person = bound_person(user_id)
        return bool(person and person.get("is_admin"))

    async def require_admin(target: Message | CallbackQuery) -> bool:
        user_id = target.from_user.id
        if is_admin(user_id):
            return True
        text = "Эта кнопка доступна только администратору."
        if isinstance(target, CallbackQuery):
            await target.answer(text, show_alert=True)
        else:
            await target.answer(text)
        return False

    @router.message(CommandStart())
    async def start(message: Message) -> None:
        person = bound_person(message.from_user.id)
        if person:
            await message.answer(
                f"Ты привязан как {person['display_name']}.",
                reply_markup=main_keyboard(bool(person.get("is_admin"))),
            )
            return
        await message.answer("Выбери себя из списка, чтобы бот мог присылать назначения.", reply_markup=bind_keyboard())

    @router.callback_query(F.data.startswith("bind:"))
    async def bind(callback: CallbackQuery) -> None:
        person_id = callback.data.split(":", 1)[1]
        store.bind_person(person_id, callback.from_user.id, callback.message.chat.id)
        person = store.data["people"][person_id]
        await callback.message.edit_text(
            f"Готово, ты привязан как {person['display_name']}.",
            reply_markup=main_keyboard(bool(person.get("is_admin"))),
        )
        await callback.answer()

    @router.message(Command("menu"))
    async def menu(message: Message) -> None:
        person = bound_person(message.from_user.id)
        await message.answer("Меню", reply_markup=main_keyboard(bool(person and person.get("is_admin"))))

    @router.message(Command("queue"))
    async def queue_command(message: Message) -> None:
        await send_queue(message)

    @router.callback_query(F.data == "queue3")
    async def queue_callback(callback: CallbackQuery) -> None:
        await send_queue(callback.message)
        await callback.answer()

    async def send_queue(message: Message) -> None:
        lines = weekly.preview(today(), 21)
        text = "Очередь на ближайшие 3 недели:\n" + ("\n".join(lines) if lines else "В ближайшие 3 недели суббот нет.")
        await message.answer(text)

    @router.callback_query(F.data == "morning7")
    async def morning_callback(callback: CallbackQuery) -> None:
        lines = morning.preview(today(), 7)
        await callback.message.answer("Утренние уборки на 7 дней:\n" + "\n".join(lines))
        await callback.answer()

    @router.message(Command("admin"))
    async def admin_command(message: Message) -> None:
        if not await require_admin(message):
            return
        await message.answer("Админ-панель", reply_markup=admin_keyboard())

    @router.callback_query(F.data == "admin")
    async def admin_callback(callback: CallbackQuery) -> None:
        if not await require_admin(callback):
            return
        await callback.message.answer("Админ-панель", reply_markup=admin_keyboard())
        await callback.answer()

    @router.callback_query(F.data.startswith("admin:menu:"))
    async def admin_submenu(callback: CallbackQuery) -> None:
        if not await require_admin(callback):
            return
        menu = callback.data.rsplit(":", 1)[1]
        if menu == "morning":
            await callback.message.answer("Настройка очереди спальника утром", reply_markup=morning_admin_keyboard())
        elif menu in WEEKLY_TASKS:
            await callback.message.answer(
                f"Настройка очереди: {WEEKLY_TASKS[menu]['title']}",
                reply_markup=weekly_admin_keyboard(menu),
            )
        else:
            await callback.answer("Неизвестное меню.", show_alert=True)
            return
        await callback.answer()

    @router.callback_query(F.data.startswith("admin:set_anchor:"))
    async def admin_set_anchor(callback: CallbackQuery, state: FSMContext) -> None:
        if not await require_admin(callback):
            return
        task_id = callback.data.rsplit(":", 1)[1]
        await state.set_state(Form.set_anchor)
        await state.update_data(task_id=task_id)
        await callback.message.answer(f"Введи дату начала круга для '{WEEKLY_TASKS[task_id]['short']}' в формате 13.06.2026.")
        await callback.answer()

    @router.message(Form.set_anchor)
    async def set_anchor_value(message: Message, state: FSMContext) -> None:
        if not await require_admin(message):
            return
        data = await state.get_data()
        try:
            day = parse_date(message.text)
            weekly.set_anchor(data["task_id"], day)
        except ValueError as error:
            await message.answer(str(error))
            return
        await state.clear()
        await message.answer("Начало круга обновлено.", reply_markup=weekly_admin_keyboard(data["task_id"]))

    @router.callback_query(F.data.startswith("admin:replace:"))
    async def admin_replace(callback: CallbackQuery, state: FSMContext) -> None:
        if not await require_admin(callback):
            return
        task_id = callback.data.rsplit(":", 1)[1]
        await state.set_state(Form.replace_weekly)
        await state.update_data(task_id=task_id)
        await callback.message.answer(
            "Введи дату и замену: `13.06.2026 Леонтьев`.\n"
            "Если нужно заменить конкретного: `13.06.2026 Орлов -> Леонтьев`.",
            parse_mode="Markdown",
        )
        await callback.answer()

    @router.message(Form.replace_weekly)
    async def replace_weekly_value(message: Message, state: FSMContext) -> None:
        if not await require_admin(message):
            return
        data = await state.get_data()
        try:
            day, old_person, new_person = _parse_weekly_replace(message.text)
            weekly.replace_person(data["task_id"], day, new_person, old_person)
        except ValueError as error:
            await message.answer(str(error))
            return
        await state.clear()
        await message.answer(
            "Замена внесена. Будущие назначения этой очереди будут пересчитаны.",
            reply_markup=weekly_admin_keyboard(data["task_id"]),
        )

    @router.callback_query(F.data.startswith("admin:add:"))
    async def admin_add(callback: CallbackQuery, state: FSMContext) -> None:
        if not await require_admin(callback):
            return
        task_id = callback.data.rsplit(":", 1)[1]
        await state.set_state(Form.add_weekly)
        await state.update_data(task_id=task_id)
        await callback.message.answer("Введи дату и второго человека: `13.06.2026 Леонтьев`.", parse_mode="Markdown")
        await callback.answer()

    @router.message(Form.add_weekly)
    async def add_weekly_value(message: Message, state: FSMContext) -> None:
        if not await require_admin(message):
            return
        data = await state.get_data()
        try:
            day, person_id = _parse_date_person(message.text)
            weekly.add_second_person(data["task_id"], day, person_id)
        except ValueError as error:
            await message.answer(str(error))
            return
        await state.clear()
        await message.answer("Усиленная уборка внесена: каждому зачтется по 0.5.", reply_markup=weekly_admin_keyboard(data["task_id"]))

    @router.callback_query(F.data.startswith("admin:skip_weekly:"))
    async def admin_skip_weekly(callback: CallbackQuery, state: FSMContext) -> None:
        if not await require_admin(callback):
            return
        task_id = callback.data.rsplit(":", 1)[1]
        await state.set_state(Form.skip_weekly)
        await state.update_data(task_id=task_id)
        await callback.message.answer("Введи дату уборки, которой не было.")
        await callback.answer()

    @router.message(Form.skip_weekly)
    async def skip_weekly_value(message: Message, state: FSMContext) -> None:
        if not await require_admin(message):
            return
        data = await state.get_data()
        try:
            day = parse_date(message.text)
            weekly.mark_skipped(data["task_id"], day)
        except ValueError as error:
            await message.answer(str(error))
            return
        await state.clear()
        await message.answer("Отмечено: уборки не было, счетчик никому не увеличен.", reply_markup=weekly_admin_keyboard(data["task_id"]))

    @router.callback_query(F.data == "admin:skip_morning")
    async def admin_skip_morning(callback: CallbackQuery, state: FSMContext) -> None:
        if not await require_admin(callback):
            return
        await state.set_state(Form.skip_morning)
        await callback.message.answer("Введи дату утренней уборки, которой не было.")
        await callback.answer()

    @router.message(Form.skip_morning)
    async def skip_morning_value(message: Message, state: FSMContext) -> None:
        if not await require_admin(message):
            return
        try:
            morning.mark_skipped(parse_date(message.text))
        except ValueError as error:
            await message.answer(str(error))
            return
        await state.clear()
        await message.answer("День пропущен, очередь сдвинута вперед.", reply_markup=morning_admin_keyboard())

    @router.callback_query(F.data == "admin:restart_morning")
    async def admin_restart_morning(callback: CallbackQuery, state: FSMContext) -> None:
        if not await require_admin(callback):
            return
        await state.set_state(Form.restart_morning)
        await callback.message.answer(
            "Введи двух уборщиков. Можно просто на завтра: `Лаврентьев Курочкин`.\n"
            "Можно с датой: `08.06.2026 Лаврентьев Курочкин`.",
            parse_mode="Markdown",
        )
        await callback.answer()

    @router.message(Form.restart_morning)
    async def restart_morning_value(message: Message, state: FSMContext) -> None:
        if not await require_admin(message):
            return
        try:
            day, first, second = _parse_morning_restart(message.text, today() + timedelta(days=1))
            morning.restart_from_pair(day, first, second)
        except ValueError as error:
            await message.answer(str(error) or "Нужно ввести два имени.")
            return
        await state.clear()
        await message.answer(f"Утренний круг перезапущен с {day.strftime('%d.%m.%Y')}.", reply_markup=morning_admin_keyboard())

    @router.callback_query(F.data.startswith("cant_weekly:"))
    async def cant_weekly(callback: CallbackQuery, state: FSMContext) -> None:
        _, task_id, work_date, person_id = callback.data.split(":")
        person = bound_person(callback.from_user.id)
        if not person or person["id"] != person_id:
            await callback.answer("Эта кнопка только для назначенного человека.", show_alert=True)
            return
        await state.set_state(Form.weekly_absence_reason)
        await state.update_data(task_id=task_id, work_date=work_date, person_id=person_id)
        await callback.message.answer("Напиши причину, почему не сможешь выполнить назначение.")
        await callback.answer()

    @router.message(Form.weekly_absence_reason)
    async def weekly_absence_reason(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        request_id = weekly.create_absence_request(
            "weekly",
            date.fromisoformat(data["work_date"]),
            data["person_id"],
            message.text or "",
            task_id=data["task_id"],
        )
        await notify_admins(
            store,
            message.bot,
            (
                f"{person_name(data['person_id'])} просит замену на {task_title(data['task_id'])} "
                f"{date.fromisoformat(data['work_date']).strftime('%d.%m.%Y')}.\n"
                f"Причина: {message.text}"
            ),
            reply_markup=absence_admin_keyboard(request_id),
        )
        await state.clear()
        await message.answer("Причина отправлена администратору.")

    @router.callback_query(F.data.startswith("absence_keep:"))
    async def absence_keep(callback: CallbackQuery) -> None:
        if not await require_admin(callback):
            return
        request_id = int(callback.data.rsplit(":", 1)[1])
        weekly.close_absence_request(request_id, "declined")
        await callback.message.answer("Оставил назначение без изменений.")
        await callback.answer()

    @router.callback_query(F.data.startswith("absence_replace:"))
    async def absence_replace(callback: CallbackQuery, state: FSMContext) -> None:
        if not await require_admin(callback):
            return
        request_id = int(callback.data.rsplit(":", 1)[1])
        await state.set_state(Form.weekly_absence_replacement)
        await state.update_data(request_id=request_id)
        await callback.message.answer("Введи имя замены.")
        await callback.answer()

    @router.message(Form.weekly_absence_replacement)
    async def weekly_absence_replacement(message: Message, state: FSMContext) -> None:
        if not await require_admin(message):
            return
        data = await state.get_data()
        request = store.absence_request(data["request_id"])
        try:
            replacement_id = parse_person(message.text)
            weekly.replace_person(
                request["task_id"],
                date.fromisoformat(request["work_date"]),
                replacement_id,
                request["requester_id"],
            )
            weekly.close_absence_request(request["id"], "approved", replacement_id)
        except ValueError as error:
            await message.answer(str(error))
            return
        await state.clear()
        await message.answer("Замена внесена.", reply_markup=weekly_admin_keyboard(request["task_id"]))

    @router.callback_query(F.data.startswith("cant_morning:"))
    async def cant_morning(callback: CallbackQuery) -> None:
        _, work_date, person_id = callback.data.split(":")
        person = bound_person(callback.from_user.id)
        if not person or person["id"] != person_id:
            await callback.answer("Эта кнопка только для назначенного человека.", show_alert=True)
            return
        day = date.fromisoformat(work_date)
        try:
            lender_id, debt_id = morning.borrow(day, person_id)
        except ValueError as error:
            await callback.answer(str(error), show_alert=True)
            return
        await notify_lender(store, callback.bot, day, person_id, lender_id, debt_id)
        await callback.message.answer(f"Принято. Запрос ушел {person_name(lender_id)}.")
        await callback.answer()

    @router.callback_query(F.data.startswith("lender_cant:"))
    async def lender_cant(callback: CallbackQuery) -> None:
        debt_id = int(callback.data.rsplit(":", 1)[1])
        try:
            work_date, borrower_id, lender_id = morning.lender_declined(debt_id)
        except ValueError as error:
            await callback.answer(str(error), show_alert=True)
            return
        person = bound_person(callback.from_user.id)
        if not person or person["id"] != lender_id:
            await callback.answer("Эта кнопка только для человека, которому пришел заем.", show_alert=True)
            return
        await notify_admins(
            store,
            callback.bot,
            (
                f"{person_name(borrower_id)} не может утром {work_date.strftime('%d.%m.%Y')}, "
                f"{person_name(lender_id)} тоже не может. Нужно ввести замену."
            ),
            reply_markup=morning_manual_keyboard(debt_id),
        )
        await callback.message.answer("Передал администратору, он вручную назначит замену.")
        await callback.answer()

    @router.callback_query(F.data.startswith("morning_manual:"))
    async def morning_manual(callback: CallbackQuery, state: FSMContext) -> None:
        if not await require_admin(callback):
            return
        debt_id = int(callback.data.rsplit(":", 1)[1])
        await state.set_state(Form.morning_debt_replacement)
        await state.update_data(debt_id=debt_id)
        await callback.message.answer("Введи имя человека, который выйдет вместо них.")
        await callback.answer()

    @router.message(Form.morning_debt_replacement)
    async def morning_debt_replacement(message: Message, state: FSMContext) -> None:
        if not await require_admin(message):
            return
        data = await state.get_data()
        try:
            replacement_id = parse_person(message.text)
            morning.manual_replacement_for_debt(data["debt_id"], replacement_id)
        except ValueError as error:
            await message.answer(str(error))
            return
        await state.clear()
        await message.answer("Ручная замена внесена, долг будет отдан этому человеку.", reply_markup=morning_admin_keyboard())

    return router


def _parse_date_person(text: str) -> tuple[date, str]:
    parts = _split_input(text)
    if len(parts) < 2:
        raise ValueError("Нужно ввести дату и имя.")
    return parse_date(parts[0]), parse_person(parts[1])


def _parse_weekly_replace(text: str) -> tuple[date, str | None, str]:
    if "->" in text:
        left, right = text.split("->", 1)
        left_parts = _split_input(left)
        if len(left_parts) < 2:
            raise ValueError("До стрелки должны быть дата и заменяемый.")
        right_parts = _split_input(right)
        if not right_parts:
            raise ValueError("После стрелки нужно ввести замену.")
        return parse_date(left_parts[0]), parse_person(left_parts[1]), parse_person(right_parts[0])
    day, person_id = _parse_date_person(text)
    return day, None, person_id


def _parse_morning_restart(text: str, default_day: date) -> tuple[date, str, str]:
    parts = _split_input(text)
    if len(parts) < 2:
        raise ValueError("Нужно ввести двух уборщиков.")
    try:
        day = parse_date(parts[0])
    except ValueError:
        day = default_day
        names = parts[:2]
    else:
        names = parts[1:3]
    if len(names) < 2:
        raise ValueError("Нужно ввести двух уборщиков.")
    return day, parse_person(names[0]), parse_person(names[1])


def _split_input(text: str) -> list[str]:
    normalized = text.replace(",", " ").replace(";", " ").replace("—", " ")
    return [part for part in normalized.split() if part]
