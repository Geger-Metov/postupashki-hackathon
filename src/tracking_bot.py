"""Tracking bot: ловит /start с параметром и логирует касание.

Запуск:
    python -m src.tracking_bot
Требует:
    export BOT_TOKEN="123:ABC..."
Пишет:
    data/touches_bot.csv
"""
from __future__ import annotations

import asyncio
import csv
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

DATA = Path("data")
DATA.mkdir(exist_ok=True)
TOUCHES_FILE = DATA / "touches_bot.csv"

START_PARAM_RE = re.compile(
    r"^c_(?P<campaign>[^_]+)_p_(?P<placement>[^_]+)_cr_(?P<creative>.+)$"
)


def log_touch(user_id: int, start_param: str) -> None:
    new_file = not TOUCHES_FILE.exists()
    with TOUCHES_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["user_id", "start_param", "timestamp", "data_source"])
        writer.writerow([
            user_id,
            start_param,
            datetime.now(timezone.utc).isoformat(),
            "collected",
        ])


def parse_start_param(sp: str) -> dict[str, str | None]:
    """Разобрать c_<campaign>_p_<placement>_cr_<creative>.

    Идентификаторы считаются opaque strings: внутри ID нельзя использовать
    дополнительный underscore. Формат валидируется целиком.
    """
    if not sp:
        return {"campaign_id": None, "placement_id": None, "creative_id": None}

    match = START_PARAM_RE.fullmatch(sp)
    if not match:
        return {"campaign_id": None, "placement_id": None, "creative_id": None}

    return {
        "campaign_id": match.group("campaign"),
        "placement_id": match.group("placement"),
        "creative_id": match.group("creative"),
    }


async def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("Set BOT_TOKEN env var")

    bot = Bot(token=token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def on_start(msg: Message) -> None:
        sp = ""
        if msg.text and " " in msg.text:
            sp = msg.text.split(" ", 1)[1].strip()

        log_touch(msg.from_user.id, sp)
        parsed = parse_start_param(sp)

        await msg.answer(
            "Привет! Записал касание.\n"
            f"campaign={parsed['campaign_id']}, "
            f"placement={parsed['placement_id']}, "
            f"creative={parsed['creative_id']}"
        )

    print("[bot] polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
