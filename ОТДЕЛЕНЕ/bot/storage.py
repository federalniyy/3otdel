from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from .constants import DEFAULT_WEEKLY_ANCHOR, PEOPLE, WEEKLY_TASKS

DORM_WEEKLY_HISTORY_SEED_KEY = "seed.dorm_weekly_history_2026_05"
DORM_WEEKLY_HISTORY_SEED = (
    ("2026-05-16", (("lavrentyev", 1.0, "primary"),)),
    ("2026-05-23", (("kazakov", 0.5, "primary"), ("orlov", 0.5, "extra"))),
    ("2026-05-30", (("kurochkin", 1.0, "primary"),)),
)
DORM_WEEKLY_SOVENKO_HISTORY_SEED_KEY = "seed.dorm_weekly_sovenko_2026_05"
DORM_WEEKLY_SOVENKO_HISTORY_SEED = (
    ("2026-05-02", (("sovenko", 1.0, "primary"),)),
    ("2026-05-09", (("sovenko", 1.0, "primary"),)),
)
DORM_WEEKLY_LEONTYEV_HISTORY_SEED_KEY = "seed.dorm_weekly_leontyev_2026_06_06"
DORM_WEEKLY_LEONTYEV_HISTORY_SEED = (
    ("2026-06-06", (("leontyev", 1.0, "primary"),)),
)


class JsonStore:
    def __init__(self, path: str):
        self.path = path
        self.in_memory = path == ":memory:"
        self.data: dict[str, Any] = self._load()
        self.bootstrap()

    def _load(self) -> dict[str, Any]:
        if self.in_memory:
            return {}
        file_path = Path(self.path)
        if not file_path.exists():
            return {}
        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def save(self) -> None:
        if self.in_memory:
            return
        file_path = Path(self.path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as file:
            json.dump(self.data, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(tmp_path, file_path)

    def bootstrap(self) -> None:
        self.data.setdefault("people", {})
        self.data.setdefault("settings", {})
        self.data.setdefault("weekly_assignments", [])
        self.data.setdefault("absence_requests", [])
        self.data.setdefault("morning_state", {"pointer": 0})
        self.data.setdefault("morning_days", {})
        self.data.setdefault("morning_debts", [])
        self.data.setdefault(
            "counters",
            {"weekly_assignment": 0, "absence_request": 0, "morning_debt": 0},
        )

        for person in PEOPLE:
            current = self.data["people"].setdefault(
                person.id,
                {
                    "id": person.id,
                    "display_name": person.name,
                    "telegram_id": None,
                    "chat_id": None,
                    "is_admin": person.id == "sharov",
                },
            )
            current["display_name"] = person.name
            if person.id == "sharov":
                current["is_admin"] = True

        for task_id in WEEKLY_TASKS:
            self.data["settings"].setdefault(
                f"{task_id}.anchor_date",
                DEFAULT_WEEKLY_ANCHOR,
            )
        self._seed_dorm_weekly_history()
        self._seed_dorm_weekly_sovenko_history()
        self._seed_dorm_weekly_leontyev_history()
        self.save()

    def _seed_dorm_weekly_history(self) -> None:
        if self.data["settings"].get(DORM_WEEKLY_HISTORY_SEED_KEY) == "applied":
            return

        for work_date, participants in DORM_WEEKLY_HISTORY_SEED:
            self.data["weekly_assignments"] = [
                assignment
                for assignment in self.data["weekly_assignments"]
                if not (
                    assignment["task_id"] == "dorm_weekly"
                    and assignment["work_date"] == work_date
                )
            ]
            self.data["weekly_assignments"].append(
                {
                    "id": self.next_id("weekly_assignment"),
                    "task_id": "dorm_weekly",
                    "work_date": work_date,
                    "status": "completed",
                    "participants": [
                        {"person_id": person_id, "weight": weight, "role": role}
                        for person_id, weight, role in participants
                    ],
                }
            )

        self.data["weekly_assignments"] = [
            assignment
            for assignment in self.data["weekly_assignments"]
            if not (
                assignment["task_id"] == "dorm_weekly"
                and assignment["status"] == "planned"
                and assignment["work_date"] > DORM_WEEKLY_HISTORY_SEED[-1][0]
            )
        ]
        self.data["settings"][DORM_WEEKLY_HISTORY_SEED_KEY] = "applied"

    def _seed_dorm_weekly_sovenko_history(self) -> None:
        if self.data["settings"].get(DORM_WEEKLY_SOVENKO_HISTORY_SEED_KEY) == "applied":
            return

        for work_date, participants in DORM_WEEKLY_SOVENKO_HISTORY_SEED:
            self.data["weekly_assignments"] = [
                assignment
                for assignment in self.data["weekly_assignments"]
                if not (
                    assignment["task_id"] == "dorm_weekly"
                    and assignment["work_date"] == work_date
                )
            ]
            self.data["weekly_assignments"].append(
                {
                    "id": self.next_id("weekly_assignment"),
                    "task_id": "dorm_weekly",
                    "work_date": work_date,
                    "status": "completed",
                    "participants": [
                        {"person_id": person_id, "weight": weight, "role": role}
                        for person_id, weight, role in participants
                    ],
                }
            )

        self.data["weekly_assignments"] = [
            assignment
            for assignment in self.data["weekly_assignments"]
            if not (
                assignment["task_id"] == "dorm_weekly"
                and assignment["status"] == "planned"
                and assignment["work_date"] > DORM_WEEKLY_SOVENKO_HISTORY_SEED[-1][0]
            )
        ]
        self.data["settings"][DORM_WEEKLY_SOVENKO_HISTORY_SEED_KEY] = "applied"

    def _seed_dorm_weekly_leontyev_history(self) -> None:
        if self.data["settings"].get(DORM_WEEKLY_LEONTYEV_HISTORY_SEED_KEY) == "applied":
            return

        for work_date, participants in DORM_WEEKLY_LEONTYEV_HISTORY_SEED:
            self.data["weekly_assignments"] = [
                assignment
                for assignment in self.data["weekly_assignments"]
                if not (
                    assignment["task_id"] == "dorm_weekly"
                    and assignment["work_date"] == work_date
                )
            ]
            self.data["weekly_assignments"].append(
                {
                    "id": self.next_id("weekly_assignment"),
                    "task_id": "dorm_weekly",
                    "work_date": work_date,
                    "status": "completed",
                    "participants": [
                        {"person_id": person_id, "weight": weight, "role": role}
                        for person_id, weight, role in participants
                    ],
                }
            )

        self.data["weekly_assignments"] = [
            assignment
            for assignment in self.data["weekly_assignments"]
            if not (
                assignment["task_id"] == "dorm_weekly"
                and assignment["status"] == "planned"
                and assignment["work_date"] > DORM_WEEKLY_LEONTYEV_HISTORY_SEED[-1][0]
            )
        ]
        self.data["settings"][DORM_WEEKLY_LEONTYEV_HISTORY_SEED_KEY] = "applied"

    def next_id(self, counter: str) -> int:
        self.data["counters"][counter] = int(self.data["counters"].get(counter, 0)) + 1
        return self.data["counters"][counter]

    def set_admin_telegram_id(self, telegram_id: int | None) -> None:
        if telegram_id is None:
            return
        self.data["people"]["sharov"]["telegram_id"] = telegram_id
        self.data["people"]["sharov"]["is_admin"] = True
        self.save()

    def bind_person(self, person_id: str, telegram_id: int, chat_id: int) -> None:
        person = self.data["people"][person_id]
        person["telegram_id"] = telegram_id
        person["chat_id"] = chat_id
        self.save()

    def person_by_telegram(self, telegram_id: int) -> dict[str, Any] | None:
        for person in self.data["people"].values():
            if person.get("telegram_id") == telegram_id:
                return person
        return None

    def people_with_chat(self, person_ids: list[str] | tuple[str, ...] | set[str]) -> list[dict[str, Any]]:
        return [
            deepcopy(self.data["people"][person_id])
            for person_id in person_ids
            if self.data["people"].get(person_id, {}).get("chat_id") is not None
        ]

    def admins(self) -> list[dict[str, Any]]:
        return [
            deepcopy(person)
            for person in self.data["people"].values()
            if person.get("is_admin") and person.get("chat_id") is not None
        ]

    def weekly_assignment(self, task_id: str, work_date: str) -> dict[str, Any] | None:
        for assignment in self.data["weekly_assignments"]:
            if assignment["task_id"] == task_id and assignment["work_date"] == work_date:
                return assignment
        return None

    def absence_request(self, request_id: int) -> dict[str, Any] | None:
        for request in self.data["absence_requests"]:
            if request["id"] == request_id:
                return request
        return None

    def morning_debt(self, debt_id: int) -> dict[str, Any] | None:
        for debt in self.data["morning_debts"]:
            if debt["id"] == debt_id:
                return debt
        return None
