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
    if not orders_path.exists():
        raise FileNotFoundError(
            f"{orders_path} — нет. Ждём Разраба №1 (load_data.py)."
        )

    df = pd.read_csv(orders_path, parse_dates=["timestamp"])
    df["date"] = df["timestamp"].dt.normalize()

    # 1. Выручка по дням
    daily = df.groupby("date")["amount"].sum()
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
    df["amount"].hist(bins=50, ax=ax)
    ax.set_title("Распределение сумм заказов")
    ax.set_xlabel("₽")
    fig.tight_layout()
    fig.savefig(FIGS / "amount_dist.png", dpi=120)
    plt.close(fig)

    # 3. Топ-10 курсов по выручке
    if "course" in df.columns:
        top = df.groupby("course")["amount"].sum().nlargest(10)
        fig, ax = plt.subplots(figsize=(10, 5))
        top.plot(kind="barh", ax=ax)
        ax.set_title("Топ-10 курсов по выручке")
        ax.invert_yaxis()
        fig.tight_layout()
        fig.savefig(FIGS / "top_courses.png", dpi=120)
        plt.close(fig)

    # 4. Аномалии
    anomalies = []
    a = df["amount"]
    anomalies.append(f"- Мин: {a.min():.2f} ₽")
    anomalies.append(f"- Макс: {a.max():.2f} ₽")
    anomalies.append(f"- Медиана: {a.median():.2f} ₽")
    suspicious = df[df["amount"].isin([463.33, 463.34, 237.50, 222.50, 225.00])]
    anomalies.append(f"- Платежи-части: {len(suspicious)} строк")
    bundles = df.groupby(["student_id", "timestamp"]).size()
    bundles = bundles[bundles > 1]
    anomalies.append(f"- Пакетных заказов (несколько курсов в одном timestamp): {len(bundles)}")

    (Path("docs") / "anomalies.md").write_text(
        "# Аномалии\n\n" + "\n".join(anomalies) + "\n",
        encoding="utf-8",
    )

    print("[eda] figures → docs/figures/")
    print("[eda] anomalies → docs/anomalies.md")


if __name__ == "__main__":
    main()