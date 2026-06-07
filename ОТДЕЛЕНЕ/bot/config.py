from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .constants import MOSCOW_TZ


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_telegram_id: int | None
    data_path: str
    timezone: str


def load_config() -> Config:
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        pass
    else:
        load_dotenv()

    admin_id = os.getenv("ADMIN_TELEGRAM_ID")
    data_path = os.getenv("DATA_PATH")
    if not data_path:
        data_dir = os.getenv("DATA_DIR")
        data_path = str(Path(data_dir) / "bot_data.json") if data_dir else "bot_data.json"
    return Config(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        admin_telegram_id=int(admin_id) if admin_id else None,
        data_path=data_path,
        timezone=os.getenv("TZ", MOSCOW_TZ),
    )
