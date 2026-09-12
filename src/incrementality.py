"""Incrementality: Interrupted Time Series (ITS).

Отвечает на вопрос: "после рекламы продажи выросли — а из-за рекламы?"

Метод: сравниваем pre-тренд и post-тренд вокруг даты поста.
Считаем lift = (post_avg − pre_avg) / pre_avg.
Это НЕ causal-модель, но отвечает на вопрос задачи 7.

Запуск:
    python -m src.incrementality --date 2026-08-08
Читает:  data/orders.csv
Пишет:   data/its_results.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path("data")


def load_daily_revenue(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df["date"] = df["timestamp"].dt.normalize()
    daily = df.groupby("date")["amount"].sum().reset_index()
    daily = daily.rename(columns={"amount": "revenue"})
    return daily.sort_values("date").reset_index(drop=True)


def its(
    daily: pd.DataFrame,
    event_date: str,
    window_days: int = 7,
) -> dict:
    """Простой ITS: pre 7 дней vs post 7 дней."""
    ev = pd.Timestamp(event_date).normalize()
    pre = daily[(daily["date"] >= ev - pd.Timedelta(days=window_days)) &
                (daily["date"] < ev)]
    post = daily[(daily["date"] >= ev) &
                 (daily["date"] < ev + pd.Timedelta(days=window_days))]

    if pre.empty or post.empty:
        return {"event_date": event_date, "status": "not enough data"}

    pre_avg = pre["revenue"].mean()
    post_avg = post["revenue"].mean()
    lift = (post_avg - pre_avg) / pre_avg if pre_avg > 0 else np.nan

    return {
        "event_date": event_date,
        "pre_days": len(pre),
        "post_days": len(post),
        "pre_avg_revenue": round(pre_avg, 2),
        "post_avg_revenue": round(post_avg, 2),
        "lift_pct": round(lift * 100, 2) if not np.isnan(lift) else None,
        "status": "ok",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--orders", default="data/orders.csv")
    ap.add_argument("--date", required=True,
                    help="Дата рекламного поста, YYYY-MM-DD")
    ap.add_argument("--window", type=int, default=7)
    args = ap.parse_args()

    path = Path(args.orders)
    if not path.exists():
        raise FileNotFoundError(f"{path} — нет. Ждём Разраба №1.")

    daily = load_daily_revenue(path)
    res = its(daily, args.date, args.window)

    out = pd.DataFrame([res])
    out.to_csv(DATA / "its_results.csv", index=False)

    print(f"[its] event: {res['event_date']} status={res['status']}")
    if res["status"] == "ok":
        print(f"[its]   pre:  {res['pre_avg_revenue']:>10.2f} ₽/день")
        print(f"[its]   post: {res['post_avg_revenue']:>10.2f} ₽/день")
        print(f"[its]   lift: {res['lift_pct']:>10.2f} %")
    print(f"[its] → data/its_results.csv")


if __name__ == "__main__":
    main()