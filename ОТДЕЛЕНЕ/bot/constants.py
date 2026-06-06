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
    },
    "toilet": {
        "title": "уборка туалета",
        "short": "туалет",
        "roster": TOILET_ROSTER,
    },
}

DEFAULT_WEEKLY_ANCHOR = "2026-06-13"
MOSCOW_TZ = "Europe/Moscow"

