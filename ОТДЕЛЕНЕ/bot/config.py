from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .constants import MOSCOW_TZ


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_telegram_id: int | None
    data_path: str
    timezone: str


def load_config() -> Config:
    load_dotenv()
    admin_id = os.getenv("ADMIN_TELEGRAM_ID")
    return Config(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        admin_telegram_id=int(admin_id) if admin_id else None,
        data_path=os.getenv("DATA_PATH", "bot_data.json"),
        timezone=os.getenv("TZ", MOSCOW_TZ),
    )
