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
TOILET_HISTORY_BALANCE_SEED_KEY = "seed.toilet_history_from_excel_2026_06_20_v2"
TOILET_HISTORY_BALANCE_SEED = (
    ("2026-03-21", (("klyus", 1.0, "primary"), ("orlov", 1.0, "extra"))),
    ("2026-03-28", (("klyus", 1.0, "primary"), ("kazakov", 1.0, "extra"))),
    ("2026-04-04", (("klyus", 1.0, "primary"), ("orlov", 1.0, "extra"))),
    ("2026-04-11", (("pilugin", 1.0, "primary"),)),
    ("2026-04-18", (("leontyev", 1.0, "primary"),)),
    ("2026-04-25", (("sovenko", 1.0, "primary"),)),
    ("2026-05-02", (("orlov", 1.0, "primary"),)),
    ("2026-05-09", (("kazakov", 1.0, "primary"),)),
    ("2026-05-16", (("leontyev", 1.0, "primary"), ("pilugin", 1.0, "extra"))),
    ("2026-05-23", (("sovenko", 1.0, "primary"),)),
    ("2026-05-30", (("kazakov", 1.0, "primary"),)),
    ("2026-06-06", (("pilugin", 1.0, "primary"),)),
    ("2026-06-13", (("pilugin", 1.0, "primary"),)),
    ("2026-06-20", (("orlov", 1.0, "primary"), ("klyus", 1.0, "extra"))),
)
FLIGHT_DECK_HISTORY_SEED_KEY = "seed.flight_deck_sharov_2026_06_20"
FLIGHT_DECK_HISTORY_SEED = (
    ("2026-06-20", (("sharov", 1.0, "primary"),)),
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
        self.data.setdefault("telegram_accounts", {})
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
        self._seed_toilet_history_balance()
        self._seed_flight_deck_history()
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

    def _seed_toilet_history_balance(self) -> None:
        if self.data["settings"].get(TOILET_HISTORY_BALANCE_SEED_KEY) == "applied":
            return

        self.data.get("count_offsets", {}).pop("toilet", None)
        self.data["weekly_assignments"] = [
            assignment
            for assignment in self.data["weekly_assignments"]
            if assignment["task_id"] != "toilet"
        ]
        for work_date, participants in TOILET_HISTORY_BALANCE_SEED:
            self.data["weekly_assignments"].append(
                {
                    "id": self.next_id("weekly_assignment"),
                    "task_id": "toilet",
                    "work_date": work_date,
                    "status": "completed",
                    "participants": [
                        {"person_id": person_id, "weight": weight, "role": role}
                        for person_id, weight, role in participants
                    ],
                }
            )

        self.data["settings"][TOILET_HISTORY_BALANCE_SEED_KEY] = "applied"

    def _seed_flight_deck_history(self) -> None:
        if self.data["settings"].get(FLIGHT_DECK_HISTORY_SEED_KEY) == "applied":
            return

        for work_date, participants in FLIGHT_DECK_HISTORY_SEED:
            self.data["weekly_assignments"] = [
                assignment
                for assignment in self.data["weekly_assignments"]
                if not (
                    assignment["task_id"] == "flight_deck"
                    and assignment["work_date"] == work_date
                )
            ]
            self.data["weekly_assignments"].append(
                {
                    "id": self.next_id("weekly_assignment"),
                    "task_id": "flight_deck",
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
            if not (assignment["task_id"] == "flight_deck" and assignment["status"] == "planned")
        ]
        self.data["settings"][FLIGHT_DECK_HISTORY_SEED_KEY] = "applied"

    def next_id(self, counter: str) -> int:
        self.data["counters"][counter] = int(self.data["counters"].get(counter, 0)) + 1
        return self.data["counters"][counter]

    def set_admin_telegram_id(self, telegram_id: int | None) -> None:
        if telegram_id is None:
            return
        self.data["people"]["sharov"]["telegram_id"] = telegram_id
        self.data["people"]["sharov"]["is_admin"] = True
        self.save()

    def remember_account(
        self,
        telegram_id: int,
        chat_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        full_name: str | None = None,
    ) -> None:
        account = self.data["telegram_accounts"].setdefault(str(telegram_id), {})
        account["telegram_id"] = telegram_id
        account["chat_id"] = chat_id
        account["username"] = username
        account["first_name"] = first_name
        account["last_name"] = last_name
        account["full_name"] = full_name or " ".join(
            item for item in (first_name, last_name) if item
        )
        self.save()

    def bind_person(
        self,
        person_id: str,
        telegram_id: int,
        chat_id: int,
        *,
        force: bool = False,
    ) -> None:
        current = self.data["people"].get(person_id)
        if (
            current
            and current.get("telegram_id") is not None
            and current.get("telegram_id") != telegram_id
            and not force
        ):
            raise ValueError("Эта фамилия уже привязана администратором.")
        for other_id, other in self.data["people"].items():
            if other_id != person_id and other.get("telegram_id") == telegram_id:
                other["telegram_id"] = None
                other["chat_id"] = None
        person = self.data["people"][person_id]
        person["telegram_id"] = telegram_id
        person["chat_id"] = chat_id
        self.save()

    def force_bind_person(self, person_id: str, telegram_id: int) -> None:
        account = self.data["telegram_accounts"].get(str(telegram_id))
        if account is None:
            for person in self.data["people"].values():
                if person.get("telegram_id") == telegram_id:
                    account = {
                        "telegram_id": telegram_id,
                        "chat_id": person.get("chat_id"),
                    }
                    break
        if not account or account.get("chat_id") is None:
            raise ValueError("Этот аккаунт еще не писал боту.")
        self.bind_person(person_id, telegram_id, int(account["chat_id"]), force=True)

    def known_accounts(self) -> list[dict[str, Any]]:
        accounts = {
            int(account["telegram_id"]): deepcopy(account)
            for account in self.data.get("telegram_accounts", {}).values()
            if account.get("telegram_id") is not None and account.get("chat_id") is not None
        }
        for person in self.data["people"].values():
            telegram_id = person.get("telegram_id")
            if telegram_id is None or person.get("chat_id") is None:
                continue
            accounts.setdefault(
                int(telegram_id),
                {
                    "telegram_id": int(telegram_id),
                    "chat_id": person["chat_id"],
                    "username": None,
                    "first_name": None,
                    "last_name": None,
                    "full_name": None,
                },
            )
        for account in accounts.values():
            bound = self.person_by_telegram(int(account["telegram_id"]))
            account["person_id"] = bound["id"] if bound else None
            account["person_name"] = bound["display_name"] if bound else None
        return sorted(
            accounts.values(),
            key=lambda item: (
                item.get("username") or "",
                item.get("full_name") or "",
                str(item["telegram_id"]),
            ),
        )

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
