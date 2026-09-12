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
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message

DATA = Path("data")
DATA.mkdir(exist_ok=True)
TOUCHES_FILE = DATA / "touches_bot.csv"


def log_touch(user_id: int, start_param: str) -> None:
    new_file = not TOUCHES_FILE.exists()
    with TOUCHES_FILE.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["user_id", "start_param", "timestamp", "data_source"])
        w.writerow([user_id, start_param, datetime.utcnow().isoformat(), "collected"])


def parse_start_param(sp: str) -> dict:
    """c_<cmp>_p_<pl>_cr_<cr> → dict."""
    if not sp or not sp.startswith("c_"):
        return {"campaign_id": None, "placement_id": None, "creative_id": None}
    parts = sp.split("_")
    out = {"campaign_id": None, "placement_id": None, "creative_id": None}
    for i, p in enumerate(parts):
        if p == "c" and i + 1 < len(parts):
            out["campaign_id"] = parts[i + 1]
        if p == "p" and i + 1 < len(parts):
            out["placement_id"] = parts[i + 1]
        if p == "cr" and i + 1 < len(parts):
            out["creative_id"] = parts[i + 1]
    return out


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
            f"Привет! Записал касание.\n"
            f"campaign={parsed['campaign_id']}, "
            f"placement={parsed['placement_id']}, "
            f"creative={parsed['creative_id']}"
        )

    print("[bot] polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())