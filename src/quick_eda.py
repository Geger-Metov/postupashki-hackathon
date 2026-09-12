"""Быстрый EDA на base.xlsx / orders.csv.

Запуск:
    python -m src.quick_eda
Пишет:
    docs/figures/*.png
    docs/anomalies.md
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

DATA = Path("data")
FIGS = Path("docs/figures")
FIGS.mkdir(parents=True, exist_ok=True)


def main() -> None:
    orders_path = DATA / "orders.csv"
    items_path = DATA / "order_items.csv"

    if not orders_path.exists():
        raise FileNotFoundError(f"{orders_path} — сначала запусти normalize_sales.")
    if not items_path.exists():
        raise FileNotFoundError(f"{items_path} — сначала запусти normalize_sales.")

    orders = pd.read_csv(orders_path, parse_dates=["timestamp"])
    items = pd.read_csv(items_path, parse_dates=["timestamp"])

    orders["date"] = orders["timestamp"].dt.normalize()

    # 1. Выручка по дням
    daily = orders.groupby("date")["total_amount"].sum()
    fig, ax = plt.subplots(figsize=(12, 4))
    daily.plot(ax=ax, marker="o")
    ax.set_title("Выручка по дням")
    ax.set_ylabel("₽")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGS / "revenue_daily.png", dpi=120)
    plt.close(fig)

    # 2. Распределение чеков
    fig, ax = plt.subplots(figsize=(10, 4))
    orders["total_amount"].hist(bins=50, ax=ax)
    ax.set_title("Распределение сумм заказов")
    ax.set_xlabel("₽")
    fig.tight_layout()
    fig.savefig(FIGS / "amount_dist.png", dpi=120)
    plt.close(fig)

    # 3. Топ-10 курсов по выручке.
    # Курс находится в order_items.csv, а не в orders.csv.
    top = items.groupby("course")["amount"].sum().nlargest(10)
    fig, ax = plt.subplots(figsize=(10, 5))
    top.sort_values().plot(kind="barh", ax=ax)
    ax.set_title("Топ-10 курсов по выручке")
    ax.set_xlabel("₽")
    fig.tight_layout()
    fig.savefig(FIGS / "top_courses.png", dpi=120)
    plt.close(fig)
    
    # 4. Краткий вывод в stdout вместо перезаписи аналитической документации.
    print("=== EDA ===")
    print(f"Строк продаж: {len(items)}")
    print(f"Заказов: {len(orders)}")
    print(f"Покупателей: {orders['student_id'].nunique()}")
    print(f"Выручка: {orders['total_amount'].sum():,.2f} ₽")
    print(f"Мин. заказ: {orders['total_amount'].min():,.2f} ₽")
    print(f"Макс. заказ: {orders['total_amount'].max():,.2f} ₽")
    print(f"Медиана заказа: {orders['total_amount'].median():,.2f} ₽")
    print(f"Пакетных заказов: {int(orders['is_bundle'].sum())}")
    print(f"Повторных заказов: {int(orders['is_repeat'].sum())}")
    print(f"Фигуры → {FIGS}/")


if __name__ == "__main__":
    main()