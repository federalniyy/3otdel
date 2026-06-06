from __future__ import annotations

from datetime import date, datetime

from .constants import PEOPLE, PEOPLE_BY_ID


def parse_date(value: str) -> date:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m"):
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        if fmt == "%d.%m":
            today = date.today()
            return date(today.year, parsed.month, parsed.day)
        return parsed.date()
    raise ValueError("Дата должна быть в формате ГГГГ-ММ-ДД или ДД.ММ.ГГГГ.")


def person_name(person_id: str) -> str:
    return PEOPLE_BY_ID[person_id].name


def parse_person(value: str) -> str:
    needle = value.strip().lower().replace("ё", "е")
    for person in PEOPLE:
        names = (person.name.lower().replace("ё", "е"), *person.aliases)
        if needle in names:
            return person.id
    raise ValueError(f"Не нашел человека: {value}")


def format_people(person_ids: list[str] | tuple[str, ...]) -> str:
    return ", ".join(person_name(person_id) for person_id in person_ids)

