from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from .constants import MORNING_ROSTER, WEEKLY_TASKS
from .keyboards import (
    absence_admin_keyboard,
    account_bindings_keyboard,
    admin_keyboard,
    binding_people_keyboard,
    bind_keyboard,
    main_keyboard,
    morning_admin_keyboard,
    morning_pair_keyboard,
    morning_manual_keyboard,
    morning_tomorrow_keyboard,
    people_keyboard,
    task_title,
    weekly_admin_keyboard,
)
from .notifications import notify_admins, notify_lender
from .services import MorningService, WeeklyService
from .storage import JsonStore
from .utils import parse_date, person_name


class Form(StatesGroup):
    set_anchor = State()
    replace_weekly = State()
    add_weekly = State()
    skip_weekly = State()
    skip_morning = State()
    weekly_absence_reason = State()


def create_router(
    store: JsonStore,
    weekly: WeeklyService,
    morning: MorningService,
    timezone: str = "Europe/Moscow",
) -> Router:
    router = Router()

    def today() -> date:
        return datetime.now(ZoneInfo(timezone)).date()

    def tomorrow() -> date:
        return today() + timedelta(days=1)

    def previous_saturday() -> date:
        current = today()
        days_since_saturday = (current.weekday() - 5) % 7
        if days_since_saturday == 0:
            days_since_saturday = 7
        return current - timedelta(days=days_since_saturday)

    def remember_user(message_or_callback: Message | CallbackQuery) -> None:
        user = message_or_callback.from_user
        message = (
            message_or_callback.message
            if isinstance(message_or_callback, CallbackQuery)
            else message_or_callback
        )
        store.remember_account(
            user.id,
            message.chat.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
        )
        person = store.person_by_telegram(user.id)
        if person and person.get("chat_id") != message.chat.id:
            store.bind_person(person["id"], user.id, message.chat.id, force=True)

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
        remember_user(message)
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
        remember_user(callback)
        person_id = callback.data.split(":", 1)[1]
        current_person = bound_person(callback.from_user.id)
        if current_person and current_person["id"] != person_id:
            await callback.answer("Ты уже привязан. Перепривязку делает администратор.", show_alert=True)
            return
        try:
            store.bind_person(person_id, callback.from_user.id, callback.message.chat.id)
        except ValueError as error:
            await callback.answer(str(error), show_alert=True)
            return
        person = store.data["people"][person_id]
        await callback.message.edit_text(
            f"Готово, ты привязан как {person['display_name']}.",
            reply_markup=main_keyboard(bool(person.get("is_admin"))),
        )
        await callback.answer()

    @router.message(Command("menu"))
    async def menu(message: Message) -> None:
        remember_user(message)
        person = bound_person(message.from_user.id)
        await message.answer("Меню", reply_markup=main_keyboard(bool(person and person.get("is_admin"))))

    @router.message(Command("queue"))
    async def queue_command(message: Message) -> None:
        remember_user(message)
        await send_queue(message)

    @router.callback_query(F.data == "queue3")
    async def queue_callback(callback: CallbackQuery) -> None:
        remember_user(callback)
        await send_queue(callback.message)
        await callback.answer()

    async def send_queue(message: Message) -> None:
        lines = weekly.preview(today(), 21)
        text = "Очередь на ближайшие 3 недели:\n" + ("\n".join(lines) if lines else "В ближайшие 3 недели суббот нет.")
        await message.answer(text)

    @router.callback_query(F.data == "morning7")
    async def morning_callback(callback: CallbackQuery) -> None:
        remember_user(callback)
        lines = morning.preview(today(), 7)
        await callback.message.answer("Утренние уборки на 7 дней:\n" + "\n".join(lines))
        await callback.answer()

    @router.message(Command("admin"))
    async def admin_command(message: Message) -> None:
        remember_user(message)
        if not await require_admin(message):
            return
        await message.answer("Админ-панель", reply_markup=admin_keyboard())

    @router.callback_query(F.data == "admin")
    async def admin_callback(callback: CallbackQuery) -> None:
        remember_user(callback)
        if not await require_admin(callback):
            return
        await callback.message.answer("Админ-панель", reply_markup=admin_keyboard())
        await callback.answer()

    @router.callback_query(F.data == "admin:bindings")
    async def admin_bindings(callback: CallbackQuery) -> None:
        remember_user(callback)
        if not await require_admin(callback):
            return
        accounts = store.known_accounts()
        text = "Выбери Telegram-аккаунт, который нужно закрепить за фамилией."
        if not accounts:
            text = "Пока нет аккаунтов. Человек должен хотя бы раз открыть бота."
        await callback.message.answer(text, reply_markup=account_bindings_keyboard(accounts))
        await callback.answer()

    @router.callback_query(F.data.startswith("admin:binding_account:"))
    async def admin_binding_account(callback: CallbackQuery) -> None:
        remember_user(callback)
        if not await require_admin(callback):
            return
        telegram_id = int(callback.data.rsplit(":", 1)[1])
        await callback.message.answer(
            "К какой фамилии привязать этот Telegram-аккаунт?",
            reply_markup=binding_people_keyboard(telegram_id),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("admin:bind_account_to:"))
    async def admin_bind_account_to(callback: CallbackQuery) -> None:
        remember_user(callback)
        if not await require_admin(callback):
            return
        _, _, telegram_id, person_id = callback.data.split(":")
        try:
            store.force_bind_person(person_id, int(telegram_id))
        except ValueError as error:
            await callback.answer(str(error), show_alert=True)
            return
        person = store.data["people"][person_id]
        await callback.message.answer(
            f"Готово: аккаунт id {telegram_id} закреплен за {person['display_name']}.",
            reply_markup=account_bindings_keyboard(store.known_accounts()),
        )
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

    @router.callback_query(F.data.startswith("admin:history_last:"))
    async def admin_history_last(callback: CallbackQuery) -> None:
        if not await require_admin(callback):
            return
        task_id = callback.data.rsplit(":", 1)[1]
        day = previous_saturday()
        await callback.message.answer(
            f"Кто выполнял {WEEKLY_TASKS[task_id]['short']} {day.strftime('%d.%m.%Y')}?",
            reply_markup=people_keyboard(
                f"admin:history_person:{task_id}:{day.isoformat()}",
                WEEKLY_TASKS[task_id]["roster"],
                back_callback=f"admin:menu:{task_id}",
            ),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("admin:history_show:"))
    async def admin_history_show(callback: CallbackQuery) -> None:
        if not await require_admin(callback):
            return
        task_id = callback.data.rsplit(":", 1)[1]
        items = weekly.history(task_id)
        if not items:
            text = "История пока пустая."
        else:
            lines = []
            for item in items:
                if item.status == "skipped":
                    lines.append(f"{item.work_date.strftime('%d.%m.%Y')}: уборки не было")
                else:
                    people = ", ".join(
                        f"{person_name(person_id)} ({weight:g})"
                        for person_id, weight in item.participants
                    )
                    lines.append(f"{item.work_date.strftime('%d.%m.%Y')}: {people}")
            text = "История уборок:\n" + "\n".join(lines)
        await callback.message.answer(text, reply_markup=weekly_admin_keyboard(task_id))
        await callback.answer()

    @router.callback_query(F.data.startswith("admin:history_person:"))
    async def admin_history_person(callback: CallbackQuery) -> None:
        if not await require_admin(callback):
            return
        _, _, task_id, work_date, person_id = callback.data.split(":")
        day = date.fromisoformat(work_date)
        try:
            weekly.record_completed(task_id, day, [person_id])
        except ValueError as error:
            await callback.answer(str(error), show_alert=True)
            return
        await callback.message.answer(
            f"Записал в историю: {WEEKLY_TASKS[task_id]['short']} {day.strftime('%d.%m.%Y')} - {person_name(person_id)}.",
            reply_markup=weekly_admin_keyboard(task_id),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("weekly_done:all:"))
    async def weekly_done_all(callback: CallbackQuery) -> None:
        if not await require_admin(callback):
            return
        work_date = callback.data.rsplit(":", 1)[1]
        day = date.fromisoformat(work_date)
        completed = weekly.complete_scheduled_for_day(day)
        if completed:
            names = ", ".join(WEEKLY_TASKS[task_id]["short"] for task_id in completed)
            text = f"Засчитал за {day.strftime('%d.%m.%Y')}: {names}."
        else:
            text = f"За {day.strftime('%d.%m.%Y')} нечего засчитывать или уже все отмечено."
        await callback.message.answer(text, reply_markup=admin_keyboard())
        await callback.answer()

    @router.callback_query(F.data.startswith("weekly_done:missing:"))
    async def weekly_done_missing(callback: CallbackQuery) -> None:
        if not await require_admin(callback):
            return
        _, _, task_id, work_date = callback.data.split(":")
        day = date.fromisoformat(work_date)
        weekly.mark_skipped(task_id, day)
        completed = weekly.complete_scheduled_for_day(day, except_task=task_id)
        text = f"Отметил: {WEEKLY_TASKS[task_id]['short']} {day.strftime('%d.%m.%Y')} не было."
        if completed:
            names = ", ".join(WEEKLY_TASKS[item]["short"] for item in completed)
            text += f" Засчитал: {names}."
        await callback.message.answer(text, reply_markup=admin_keyboard())
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
        await callback.message.answer("Введи дату уборки. После этого выберешь человека кнопкой.")
        await callback.answer()

    @router.message(Form.replace_weekly)
    async def replace_weekly_value(message: Message, state: FSMContext) -> None:
        if not await require_admin(message):
            return
        data = await state.get_data()
        try:
            day = parse_date(message.text)
            assignment = weekly.ensure_assignment(data["task_id"], day)
        except ValueError as error:
            await message.answer(str(error))
            return
        if assignment is None:
            await message.answer("На эту дату уборка не запланирована.")
            return
        await state.clear()
        participants = [person_id for person_id, _ in assignment.participants]
        if len(participants) > 1:
            await message.answer(
                "Кого заменить?",
                reply_markup=people_keyboard(
                    f"wr_old:{data['task_id']}:{day.strftime('%Y%m%d')}",
                    participants,
                    back_callback=f"admin:menu:{data['task_id']}",
                ),
            )
            return
        old_person = participants[0] if participants else "none"
        await message.answer(
            "Кого поставить вместо него?",
            reply_markup=people_keyboard(
                f"wr_new:{data['task_id']}:{day.strftime('%Y%m%d')}:{old_person}",
                WEEKLY_TASKS[data["task_id"]]["roster"],
                back_callback=f"admin:menu:{data['task_id']}",
            ),
        )

    @router.callback_query(F.data.startswith("wr_old:"))
    async def weekly_replace_old(callback: CallbackQuery) -> None:
        if not await require_admin(callback):
            return
        _, task_id, work_date, old_person = callback.data.split(":")
        await callback.message.answer(
            "Кого поставить вместо него?",
            reply_markup=people_keyboard(
                f"wr_new:{task_id}:{work_date}:{old_person}",
                WEEKLY_TASKS[task_id]["roster"],
                back_callback=f"admin:menu:{task_id}",
            ),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("wr_new:"))
    async def weekly_replace_new(callback: CallbackQuery) -> None:
        if not await require_admin(callback):
            return
        _, task_id, work_date, old_person, new_person = callback.data.split(":")
        day = datetime.strptime(work_date, "%Y%m%d").date()
        try:
            weekly.replace_person(task_id, day, new_person, None if old_person == "none" else old_person)
        except ValueError as error:
            await callback.answer(str(error), show_alert=True)
            return
        await callback.message.answer(
            "Замена внесена. Будущие назначения этой очереди будут пересчитаны.",
            reply_markup=weekly_admin_keyboard(task_id),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("admin:add:"))
    async def admin_add(callback: CallbackQuery, state: FSMContext) -> None:
        if not await require_admin(callback):
            return
        task_id = callback.data.rsplit(":", 1)[1]
        await state.set_state(Form.add_weekly)
        await state.update_data(task_id=task_id)
        await callback.message.answer("Введи дату уборки. После этого выберешь второго человека кнопкой.")
        await callback.answer()

    @router.message(Form.add_weekly)
    async def add_weekly_value(message: Message, state: FSMContext) -> None:
        if not await require_admin(message):
            return
        data = await state.get_data()
        try:
            day = parse_date(message.text)
        except ValueError as error:
            await message.answer(str(error))
            return
        await state.clear()
        await message.answer(
            "Выбери второго человека:",
            reply_markup=people_keyboard(
                f"admin:add_weekly_person:{data['task_id']}:{day.isoformat()}",
                WEEKLY_TASKS[data["task_id"]]["roster"],
                back_callback=f"admin:menu:{data['task_id']}",
            ),
        )

    @router.callback_query(F.data.startswith("admin:add_weekly_person:"))
    async def add_weekly_person(callback: CallbackQuery) -> None:
        if not await require_admin(callback):
            return
        _, _, task_id, work_date, person_id = callback.data.split(":")
        try:
            weekly.add_second_person(task_id, date.fromisoformat(work_date), person_id)
        except ValueError as error:
            await callback.answer(str(error), show_alert=True)
            return
        await callback.message.answer(
            "Усиленная уборка внесена: каждому зачтется по 0.5.",
            reply_markup=weekly_admin_keyboard(task_id),
        )
        await callback.answer()

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
        await callback.message.answer(
            f"Выбери пару, с которой начать утренний круг {tomorrow().strftime('%d.%m.%Y')}:",
            reply_markup=morning_pair_keyboard(tomorrow().isoformat()),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("admin:morning_pair:"))
    async def morning_pair(callback: CallbackQuery) -> None:
        if not await require_admin(callback):
            return
        _, _, work_date, first_id, second_id = callback.data.split(":")
        day = date.fromisoformat(work_date)
        try:
            morning.restart_from_pair(day, first_id, second_id)
        except ValueError as error:
            await callback.answer(str(error), show_alert=True)
            return
        await callback.message.answer(
            f"Утренний круг перезапущен с {day.strftime('%d.%m.%Y')}: {person_name(first_id)} и {person_name(second_id)}.",
            reply_markup=morning_admin_keyboard(),
        )
        await callback.answer()

    @router.callback_query(F.data == "admin:morning_tomorrow")
    async def admin_morning_tomorrow(callback: CallbackQuery) -> None:
        if not await require_admin(callback):
            return
        day = tomorrow()
        slots = morning.ensure_day(day)
        await callback.message.answer(
            f"Уборщики на завтра, {day.strftime('%d.%m.%Y')}:",
            reply_markup=morning_tomorrow_keyboard(day.isoformat(), slots),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("admin:replace_morning_slot:"))
    async def replace_morning_slot(callback: CallbackQuery) -> None:
        if not await require_admin(callback):
            return
        _, _, work_date, slot_no = callback.data.split(":")
        await callback.message.answer(
            "Выбери замену:",
            reply_markup=people_keyboard(
                f"admin:set_morning_slot:{work_date}:{slot_no}",
                MORNING_ROSTER,
                back_callback="admin:morning_tomorrow",
            ),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("admin:set_morning_slot:"))
    async def set_morning_slot(callback: CallbackQuery) -> None:
        if not await require_admin(callback):
            return
        _, _, work_date, slot_no, person_id = callback.data.split(":")
        day = date.fromisoformat(work_date)
        try:
            morning.replace_slot(day, int(slot_no), person_id)
        except ValueError as error:
            await callback.answer(str(error), show_alert=True)
            return
        slots = morning.ensure_day(day)
        await callback.message.answer(
            f"Замена на {day.strftime('%d.%m.%Y')} внесена.",
            reply_markup=morning_tomorrow_keyboard(day.isoformat(), slots),
        )
        await callback.answer()

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
        request = store.absence_request(request_id)
        if not request:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return
        await callback.message.answer(
            "Выбери замену:",
            reply_markup=people_keyboard(
                f"admin:absence_person:{request_id}",
                WEEKLY_TASKS[request["task_id"]]["roster"],
                back_callback=f"admin:menu:{request['task_id']}",
            ),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("admin:absence_person:"))
    async def absence_person(callback: CallbackQuery) -> None:
        if not await require_admin(callback):
            return
        _, _, request_id, replacement_id = callback.data.split(":")
        request = store.absence_request(int(request_id))
        if not request:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return
        try:
            weekly.replace_person(
                request["task_id"],
                date.fromisoformat(request["work_date"]),
                replacement_id,
                request["requester_id"],
            )
            weekly.close_absence_request(request["id"], "approved", replacement_id)
        except ValueError as error:
            await callback.answer(str(error), show_alert=True)
            return
        await callback.message.answer("Замена внесена.", reply_markup=weekly_admin_keyboard(request["task_id"]))
        await callback.answer()

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
        await callback.message.answer(
            "Выбери человека, который выйдет вместо них:",
            reply_markup=people_keyboard(
                f"admin:debt_person:{debt_id}",
                MORNING_ROSTER,
                back_callback="admin:menu:morning",
            ),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("admin:debt_person:"))
    async def debt_person(callback: CallbackQuery) -> None:
        if not await require_admin(callback):
            return
        _, _, debt_id, replacement_id = callback.data.split(":")
        try:
            morning.manual_replacement_for_debt(int(debt_id), replacement_id)
        except ValueError as error:
            await callback.answer(str(error), show_alert=True)
            return
        await callback.message.answer(
            "Ручная замена внесена, долг будет отдан этому человеку.",
            reply_markup=morning_admin_keyboard(),
        )
        await callback.answer()

    @router.callback_query(F.data == "noop")
    async def noop(callback: CallbackQuery) -> None:
        await callback.answer()

    return router
