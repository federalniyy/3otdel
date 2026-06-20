from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Person:
    id: str
    name: str
    aliases: tuple[str, ...] = ()


PEOPLE: tuple[Person, ...] = (
    Person("sharov", "Шаров", ("шаров", "командир")),
    Person("klyus", "Клюс", ("клюс",)),
    Person("leontyev", "Леонтьев", ("леонтьев", "леонтьеву")),
    Person("orlov", "Орлов", ("орлов",)),
    Person("pilugin", "Пилюгин", ("пилюгин",)),
    Person("sovenko", "Совенко", ("совенко",)),
    Person("kazakov", "Казаков", ("казаков",)),
    Person("lavrentyev", "Лаврентьев", ("лаврентьев",)),
    Person("kurochkin", "Курочкин", ("курочкин",)),
)

PEOPLE_BY_ID = {person.id: person for person in PEOPLE}

DORM_WEEKLY_ROSTER = (
    "sharov",
    "leontyev",
    "orlov",
    "pilugin",
    "sovenko",
    "kazakov",
    "lavrentyev",
    "kurochkin",
)

TOILET_ROSTER = (
    "klyus",
    "leontyev",
    "orlov",
    "pilugin",
    "sovenko",
    "kazakov",
)

FLIGHT_DECK_ROSTER = (
    "sharov",
    "klyus",
    "leontyev",
    "orlov",
    "pilugin",
    "sovenko",
    "kazakov",
)

MORNING_ROSTER = (
    "lavrentyev",
    "kurochkin",
    "leontyev",
    "orlov",
    "pilugin",
    "sovenko",
    "kazakov",
)

WEEKLY_TASKS = {
    "dorm_weekly": {
        "title": "субботняя уборка спального помещения",
        "short": "спальник",
        "roster": DORM_WEEKLY_ROSTER,
        "schedule": "weekly",
        "weight_mode": "split",
        "show_in_queue": True,
        "notify": True,
        "confirm": True,
        "auto_complete": True,
    },
    "toilet": {
        "title": "уборка туалета",
        "short": "туалет",
        "roster": TOILET_ROSTER,
        "schedule": "two_on_one_off",
        "weight_mode": "per_person",
        "show_in_queue": True,
        "notify": True,
        "confirm": True,
        "auto_complete": True,
    },
    "flight_deck": {
        "title": "субботняя взлетка",
        "short": "взлетка",
        "roster": FLIGHT_DECK_ROSTER,
        "schedule": "weekly",
        "weight_mode": "split",
        "show_in_queue": False,
        "notify": False,
        "confirm": False,
        "auto_complete": False,
    },
}

DEFAULT_WEEKLY_ANCHOR = "2026-06-13"
MOSCOW_TZ = "Europe/Moscow"

