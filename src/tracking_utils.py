"""Утилиты для tracking: парсинг start_param без зависимости от aiogram."""
from __future__ import annotations

import re


START_PARAM_RE = re.compile(
    r"^c_(?P<campaign>[^_]+)"
    r"_p_(?P<placement>[^_]+)"
    r"_cr_(?P<creative>.+)$"
)


def parse_start_param(sp: str) -> dict[str, str | None]:
    """c_<cmp>_p_<pl>_cr_<cr> → dict. Безопасен к пустым/кривым строкам."""
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