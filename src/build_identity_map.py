"""Identity map: telegram_user_id ↔ student_id.

В production это разные ID. Для MVP используется mock mapping:
telegram_user_id = str(student_id), помеченный synthetic_deterministic.

Запуск:
    python -m src.build_identity_map
Читает:  data/orders.csv
Пишет:   data/identity_map.csv
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def build_identity_map(
    orders_path: Path = Path("data/orders.csv"),
    output_path: Path = Path("data/identity_map.csv"),
) -> pd.DataFrame:
    if not orders_path.exists():
        raise FileNotFoundError(
            f"{orders_path} — нет. Ждём Разраба №1."
        )

    orders = pd.read_csv(orders_path)

    result = (
        orders[["student_id"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    # MOCK ONLY:
    # в production mapping приходит из CRM / tracking link / Telegram bot.
    # В MVP мы просто помечаем, что связь детерминированная и с confidence = 1.0
    result["telegram_user_id"] = result["student_id"].astype(str)
    result["mapping_method"] = "synthetic_deterministic"
    result["confidence"] = 1.0

    result = result[
        ["telegram_user_id", "student_id", "mapping_method", "confidence"]
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)

    print(f"[identity_map] {len(result)} mappings → {output_path}")
    return result


def main() -> None:
    build_identity_map()


if __name__ == "__main__":
    main()