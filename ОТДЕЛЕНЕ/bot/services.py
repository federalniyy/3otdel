from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, timedelta

from .constants import MORNING_ROSTER, WEEKLY_TASKS
from .storage import JsonStore
from .utils import person_name


@dataclass(frozen=True)
class WeeklyAssignment:
    task_id: str
    work_date: date
    status: str
    participants: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class MorningSlot:
    slot_no: int
    original_person_id: str
    person_id: str
    source: str


class WeeklyService:
    def __init__(self, store: JsonStore):
        self.store = store

    def set_anchor(self, task_id: str, anchor: date) -> None:
        self._check_task(task_id)
        self.store.data["settings"][f"{task_id}.anchor_date"] = anchor.isoformat()
        self.store.data["weekly_assignments"] = [
            assignment
            for assignment in self.store.data["weekly_assignments"]
            if not (assignment["task_id"] == task_id and assignment["status"] == "planned")
        ]
        self.store.save()

    def anchor(self, task_id: str) -> date:
        self._check_task(task_id)
        return date.fromisoformat(self.store.data["settings"][f"{task_id}.anchor_date"])

    def is_cleaning_saturday(self, task_id: str, day: date) -> bool:
        if day.weekday() != 5:
            return False
        weeks = (day - self.anchor(task_id)).days // 7
        return weeks >= 0 and weeks % 3 in (0, 1)

    def ensure_assignment(self, task_id: str, day: date) -> WeeklyAssignment | None:
        self._check_task(task_id)
        existing = self.get_assignment(task_id, day)
        if existing:
            return existing
        if not self.is_cleaning_saturday(task_id, day):
            return None
        assignment = {
            "id": self.store.next_id("weekly_assignment"),
            "task_id": task_id,
            "work_date": day.isoformat(),
            "status": "planned",
            "participants": [
                {
                    "person_id": self._pick_person(task_id, day),
                    "weight": 1.0,
                    "role": "primary",
                }
            ],
        }
        self.store.data["weekly_assignments"].append(assignment)
        self.store.save()
        return self.get_assignment(task_id, day)

    def get_assignment(self, task_id: str, day: date) -> WeeklyAssignment | None:
        assignment = self.store.weekly_assignment(task_id, day.isoformat())
        if not assignment:
            return None
        return WeeklyAssignment(
            task_id=task_id,
            work_date=day,
            status=assignment["status"],
            participants=tuple(
                (participant["person_id"], float(participant["weight"]))
                for participant in sorted(assignment["participants"], key=lambda item: item["role"])
            ),
        )

    def replace_person(
        self,
        task_id: str,
        day: date,
        new_person_id: str,
        old_person_id: str | None = None,
    ) -> None:
        self._check_member(task_id, new_person_id)
        self.ensure_assignment(task_id, day)
        assignment = self.store.weekly_assignment(task_id, day.isoformat())
        if not assignment:
            raise ValueError("На эту дату уборка не запланирована.")
        participants = assignment["participants"]
        target = None
        if old_person_id:
            for participant in participants:
                if participant["person_id"] == old_person_id:
                    target = participant
                    break
        else:
            target = participants[0] if participants else None
            if target is None:
                participants.append(
                    {"person_id": new_person_id, "weight": 1.0, "role": "primary"}
                )
                assignment["status"] = "planned"
                self._drop_future_planned(task_id, day)
                self.store.save()
                return
        if target is None:
            raise ValueError("Не нашел заменяемого в этом назначении.")
        target["person_id"] = new_person_id
        assignment["status"] = "planned"
        self._drop_future_planned(task_id, day)
        self.store.save()

    def add_second_person(self, task_id: str, day: date, person_id: str) -> None:
        self._check_member(task_id, person_id)
        self.ensure_assignment(task_id, day)
        assignment = self.store.weekly_assignment(task_id, day.isoformat())
        if not assignment:
            raise ValueError("На эту дату уборка не запланирована.")
        if any(item["person_id"] == person_id for item in assignment["participants"]):
            raise ValueError("Этот человек уже стоит в назначении.")
        if len(assignment["participants"]) >= 2:
            raise ValueError("Для усиленной уборки уже назначены два человека.")
        for participant in assignment["participants"]:
            participant["weight"] = 0.5
        assignment["participants"].append(
            {"person_id": person_id, "weight": 0.5, "role": "extra"}
        )
        assignment["status"] = "planned"
        self._drop_future_planned(task_id, day)
        self.store.save()

    def mark_skipped(self, task_id: str, day: date) -> None:
        assignment = self.store.weekly_assignment(task_id, day.isoformat())
        if assignment is None:
            assignment = {
                "id": self.store.next_id("weekly_assignment"),
                "task_id": task_id,
                "work_date": day.isoformat(),
                "status": "skipped",
                "participants": [],
            }
            self.store.data["weekly_assignments"].append(assignment)
        else:
            assignment["status"] = "skipped"
            assignment["participants"] = []
        self._drop_future_planned(task_id, day)
        self.store.save()

    def create_absence_request(
        self,
        task_kind: str,
        work_date: date,
        requester_id: str,
        reason: str,
        task_id: str | None = None,
    ) -> int:
        request_id = self.store.next_id("absence_request")
        self.store.data["absence_requests"].append(
            {
                "id": request_id,
                "task_kind": task_kind,
                "task_id": task_id,
                "work_date": work_date.isoformat(),
                "requester_id": requester_id,
                "reason": reason,
                "status": "pending",
                "replacement_id": None,
            }
        )
        self.store.save()
        return request_id

    def close_absence_request(
        self,
        request_id: int,
        status: str,
        replacement_id: str | None = None,
    ) -> None:
        request = self.store.absence_request(request_id)
        if not request:
            raise ValueError("Заявка не найдена.")
        request["status"] = status
        request["replacement_id"] = replacement_id
        self.store.save()

    def preview(self, start: date, days: int = 21) -> list[str]:
        lines: list[str] = []
        for offset in range(days + 1):
            day = start + timedelta(days=offset)
            if day.weekday() != 5:
                continue
            parts = [day.strftime("%d.%m.%Y")]
            for task_id in WEEKLY_TASKS:
                if not self.is_cleaning_saturday(task_id, day):
                    parts.append(f"{WEEKLY_TASKS[task_id]['short']}: нет уборки")
                    continue
                assignment = self.ensure_assignment(task_id, day)
                assert assignment is not None
                if assignment.status == "skipped":
                    parts.append(f"{WEEKLY_TASKS[task_id]['short']}: уборки не было")
                else:
                    names = ", ".join(
                        f"{person_name(pid)} ({weight:g})"
                        for pid, weight in assignment.participants
                    )
                    parts.append(f"{WEEKLY_TASKS[task_id]['short']}: {names}")
            lines.append(" | ".join(parts))
        return lines

    def counts(self, task_id: str) -> dict[str, float]:
        roster = WEEKLY_TASKS[task_id]["roster"]
        counts = {person_id: 0.0 for person_id in roster}
        for assignment in self.store.data["weekly_assignments"]:
            if assignment["task_id"] != task_id or assignment["status"] not in ("planned", "completed"):
                continue
            for participant in assignment["participants"]:
                counts[participant["person_id"]] += float(participant["weight"])
        return counts

    def _pick_person(self, task_id: str, day: date) -> str:
        roster = WEEKLY_TASKS[task_id]["roster"]
        counts = self.counts(task_id)
        blocked = self._same_week_participants(day, except_task=task_id)
        candidates = [person_id for person_id in roster if person_id not in blocked]
        if not candidates:
            candidates = list(roster)
        return min(candidates, key=lambda person_id: (counts[person_id], roster.index(person_id)))

    def _same_week_participants(self, day: date, except_task: str) -> set[str]:
        monday = day - timedelta(days=day.weekday())
        sunday = monday + timedelta(days=6)
        blocked = set()
        for assignment in self.store.data["weekly_assignments"]:
            if assignment["task_id"] == except_task or assignment["status"] not in ("planned", "completed"):
                continue
            work_date = date.fromisoformat(assignment["work_date"])
            if monday <= work_date <= sunday:
                blocked.update(participant["person_id"] for participant in assignment["participants"])
        return blocked

    def _check_task(self, task_id: str) -> None:
        if task_id not in WEEKLY_TASKS:
            raise ValueError(f"Неизвестная работа: {task_id}")

    def _check_member(self, task_id: str, person_id: str) -> None:
        if person_id not in WEEKLY_TASKS[task_id]["roster"]:
            raise ValueError("Этот человек не входит в очередь этой работы.")

    def _drop_future_planned(self, task_id: str, changed_day: date) -> None:
        changed = changed_day.isoformat()
        self.store.data["weekly_assignments"] = [
            assignment
            for assignment in self.store.data["weekly_assignments"]
            if not (
                assignment["task_id"] == task_id
                and assignment["status"] == "planned"
                and assignment["work_date"] > changed
            )
        ]


class MorningService:
    def __init__(self, store: JsonStore):
        self.store = store

    def ensure_day(self, day: date) -> list[MorningSlot]:
        existing = self.get_day(day)
        if existing is not None:
            return existing
        previous_days = sorted(
            date.fromisoformat(work_date)
            for work_date in self.store.data["morning_days"]
            if work_date < day.isoformat()
        )
        if previous_days:
            cursor = previous_days[-1] + timedelta(days=1)
            while cursor <= day:
                if self.get_day(cursor) is None:
                    self._create_day(cursor)
                cursor += timedelta(days=1)
            return self.get_day(day) or []
        self._create_day(day)
        return self.get_day(day) or []

    def _create_day(self, day: date) -> None:
        pointer_before = int(self.store.data["morning_state"]["pointer"])
        pointer = pointer_before
        rows = []
        paid_debts = []
        for slot_no in (1, 2):
            original = MORNING_ROSTER[pointer]
            pointer = (pointer + 1) % len(MORNING_ROSTER)
            debt = self._open_debt_for_lender(original)
            if debt:
                rows.append(
                    {
                        "slot_no": slot_no,
                        "original_person_id": original,
                        "person_id": debt["borrower_id"],
                        "source": "debt",
                    }
                )
                paid_debts.append(debt)
            else:
                rows.append(
                    {
                        "slot_no": slot_no,
                        "original_person_id": original,
                        "person_id": original,
                        "source": "normal",
                    }
                )
        self.store.data["morning_days"][day.isoformat()] = {
            "status": "planned",
            "pointer_before": pointer_before,
            "pointer_after": pointer,
            "slots": rows,
        }
        self.store.data["morning_state"]["pointer"] = pointer
        for debt in paid_debts:
            debt["status"] = "paid"
            debt["paid_date"] = day.isoformat()
        self.store.save()

    def get_day(self, day: date) -> list[MorningSlot] | None:
        record = self.store.data["morning_days"].get(day.isoformat())
        if record is None:
            return None
        if record["status"] == "skipped":
            return []
        return [
            MorningSlot(
                slot_no=slot["slot_no"],
                original_person_id=slot["original_person_id"],
                person_id=slot["person_id"],
                source=slot["source"],
            )
            for slot in sorted(record["slots"], key=lambda item: item["slot_no"])
        ]

    def preview(self, start: date, days: int = 7) -> list[str]:
        lines = []
        for offset in range(days):
            day = start + timedelta(days=offset)
            slots = self.ensure_day(day)
            if not slots:
                lines.append(f"{day.strftime('%d.%m.%Y')}: уборки не было")
                continue
            names = ", ".join(
                f"{person_name(slot.person_id)}"
                + (
                    f" за {person_name(slot.original_person_id)}"
                    if slot.person_id != slot.original_person_id
                    else ""
                )
                for slot in slots
            )
            lines.append(f"{day.strftime('%d.%m.%Y')}: {names}")
        return lines

    def borrow(self, day: date, borrower_id: str) -> tuple[str, int]:
        slots = self.ensure_day(day)
        if borrower_id not in [slot.person_id for slot in slots]:
            raise ValueError("Этот человек не назначен на указанную утреннюю уборку.")
        assigned = {slot.person_id for slot in slots}
        lender_id = self._next_lender(borrower_id, assigned)
        record = self.store.data["morning_days"][day.isoformat()]
        slot = next(slot for slot in record["slots"] if slot["person_id"] == borrower_id)
        slot["person_id"] = lender_id
        slot["source"] = "borrow"
        debt_id = self.store.next_id("morning_debt")
        self.store.data["morning_debts"].append(
            {
                "id": debt_id,
                "borrower_id": borrower_id,
                "lender_id": lender_id,
                "created_for_date": day.isoformat(),
                "paid_date": None,
                "status": "open",
            }
        )
        self.store.save()
        return lender_id, debt_id

    def lender_declined(self, debt_id: int) -> tuple[date, str, str]:
        debt = self.store.morning_debt(debt_id)
        if debt is None or debt["status"] != "open":
            raise ValueError("Долг не найден или уже закрыт.")
        return date.fromisoformat(debt["created_for_date"]), debt["borrower_id"], debt["lender_id"]

    def manual_replacement_for_debt(self, debt_id: int, replacement_id: str) -> None:
        if replacement_id not in MORNING_ROSTER:
            raise ValueError("Этот человек не участвует в утренней очереди.")
        debt = self.store.morning_debt(debt_id)
        if debt is None or debt["status"] != "open":
            raise ValueError("Долг не найден или уже закрыт.")
        record = self.store.data["morning_days"][debt["created_for_date"]]
        for slot in record["slots"]:
            if slot["original_person_id"] == debt["borrower_id"]:
                slot["person_id"] = replacement_id
                slot["source"] = "manual_borrow"
                break
        debt["lender_id"] = replacement_id
        self.store.save()

    def mark_skipped(self, day: date) -> None:
        self.ensure_day(day)
        key = day.isoformat()
        record = deepcopy(self.store.data["morning_days"][key])
        future_keys = sorted(
            work_date for work_date in self.store.data["morning_days"] if work_date >= key
        )
        for debt in self.store.data["morning_debts"]:
            if debt.get("paid_date") in future_keys:
                debt["status"] = "open"
                debt["paid_date"] = None
        for future_key in future_keys:
            del self.store.data["morning_days"][future_key]
        self.store.data["morning_days"][key] = {
            "status": "skipped",
            "pointer_before": record["pointer_before"],
            "pointer_after": record["pointer_before"],
            "slots": [],
        }
        self.store.data["morning_state"]["pointer"] = record["pointer_before"]
        self.store.save()

    def restart_from_pair(self, day: date, first_id: str, second_id: str) -> None:
        for person_id in (first_id, second_id):
            if person_id not in MORNING_ROSTER:
                raise ValueError("В утренней уборке участвуют только спальник без командира.")
        pointer_before = MORNING_ROSTER.index(first_id)
        pointer_after = (MORNING_ROSTER.index(second_id) + 1) % len(MORNING_ROSTER)
        key = day.isoformat()
        for future_key in sorted(
            work_date for work_date in self.store.data["morning_days"] if work_date >= key
        ):
            del self.store.data["morning_days"][future_key]
        self.store.data["morning_days"][key] = {
            "status": "planned",
            "pointer_before": pointer_before,
            "pointer_after": pointer_after,
            "slots": [
                {
                    "slot_no": 1,
                    "original_person_id": first_id,
                    "person_id": first_id,
                    "source": "manual_restart",
                },
                {
                    "slot_no": 2,
                    "original_person_id": second_id,
                    "person_id": second_id,
                    "source": "manual_restart",
                },
            ],
        }
        self.store.data["morning_state"]["pointer"] = pointer_after
        self.store.save()

    def _open_debt_for_lender(self, lender_id: str) -> dict | None:
        debts = [
            debt
            for debt in self.store.data["morning_debts"]
            if debt["lender_id"] == lender_id and debt["status"] == "open"
        ]
        return min(debts, key=lambda debt: debt["id"]) if debts else None

    def _next_lender(self, borrower_id: str, assigned_today: set[str]) -> str:
        start = MORNING_ROSTER.index(borrower_id)
        for step in range(1, len(MORNING_ROSTER)):
            candidate = MORNING_ROSTER[(start + step) % len(MORNING_ROSTER)]
            if candidate not in assigned_today:
                return candidate
        raise ValueError("Не удалось найти следующего человека для займа.")
