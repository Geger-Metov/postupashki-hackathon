"""Tracking bot: ловит /start с параметром и логирует касание + stitching.

Запуск:
    $env:BOT_TOKEN="123:ABC..."
    python -m src.tracking_bot

Пишет:
    data/touches_bot.csv
    data/user_stitching.csv
"""
from __future__ import annotations

import asyncio
import csv
import os
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.tracking_utils import parse_start_param

DATA = Path("data")
DATA.mkdir(exist_ok=True)
TOUCHES_FILE = DATA / "touches_bot.csv"
STITCHING_FILE = DATA / "user_stitching.csv"


def _append_csv(path: Path, header: list[str], row: list) -> None:
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(header)
        w.writerow(row)


def log_touch(user_id: int, start_param: str) -> None:
    _append_csv(
        TOUCHES_FILE,
        ["user_id", "start_param", "timestamp", "data_source"],
        [user_id, start_param, datetime.utcnow().isoformat(), "collected"],
    )


def log_stitching(user_id: int, start_param: str) -> None:
    parsed = parse_start_param(start_param)
    _append_csv(
        STITCHING_FILE,
        [
            "telegram_user_id", "start_param", "campaign_id",
            "placement_id", "creative_id", "first_seen",
        ],
        [
            user_id, start_param,
            parsed["campaign_id"], parsed["placement_id"], parsed["creative_id"],
            datetime.utcnow().isoformat(),
        ],
    )


async def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("Set BOT_TOKEN env var: $env:BOT_TOKEN='...'")

    bot = Bot(token=token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def on_start(msg: Message) -> None:
        sp = ""
        if msg.text and " " in msg.text:
            sp = msg.text.split(" ", 1)[1].strip()

        log_touch(msg.from_user.id, sp)
        log_stitching(msg.from_user.id, sp)

        parsed = parse_start_param(sp)
        await msg.answer(
            f"Привет! Записал касание.\n"
            f"campaign={parsed['campaign_id']}, "
            f"placement={parsed['placement_id']}, "
            f"creative={parsed['creative_id']}"
        )

    print("[bot] polling... (Ctrl+C to stop)")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())