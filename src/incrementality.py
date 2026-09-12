"""
Важно:
    Текущая реализация НЕ является полноценным Interrupted Time Series.
    Она сравнивает среднюю дневную выручку в pre/post окнах и поэтому
    должна интерпретироваться как exploratory analysis, а не как
    causal estimate.

Запуск:
    python -m src.incrementality --date 2026-08-08
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
    daily = (
        df.groupby("date", as_index=False)
        .agg(revenue=("total_amount", "sum"))
        .sort_values("date")
        .reset_index(drop=True)
    )
    return daily


def pre_post_analysis(
    daily: pd.DataFrame,
    event_date: str,
    window_days: int = 7,
) -> dict:
    """Сравнить среднюю выручку до и после события.

    Это descriptive/pre-post analysis, не causal ITS.
    """
    if window_days <= 0:
        raise ValueError("window_days должен быть > 0")

    ev = pd.Timestamp(event_date).normalize()
    pre = daily[
        (daily["date"] >= ev - pd.Timedelta(days=window_days))
        & (daily["date"] < ev)
    ]
    post = daily[
        (daily["date"] >= ev)
        & (daily["date"] < ev + pd.Timedelta(days=window_days))
    ]

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
        "method": "pre_post_descriptive",
    }


# Backward-compatible alias for existing imports.
its = pre_post_analysis


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--orders", default="data/orders.csv")
    ap.add_argument("--date", required=True, help="Дата события, YYYY-MM-DD")
    ap.add_argument("--window", type=int, default=7)
    args = ap.parse_args()

    path = Path(args.orders)
    if not path.exists():
        raise FileNotFoundError(f"{path} — сначала запусти normalize_sales.")

    daily = load_daily_revenue(path)
    res = pre_post_analysis(daily, args.date, args.window)

    out = DATA / "its_results.csv"
    pd.DataFrame([res]).to_csv(out, index=False)

    print(f"[incrementality] event={res['event_date']} status={res['status']}")
    if res["status"] == "ok":
        print(f"[incrementality] pre:  {res['pre_avg_revenue']:,.2f} ₽/день")
        print(f"[incrementality] post: {res['post_avg_revenue']:,.2f} ₽/день")
        print(f"[incrementality] lift: {res['lift_pct']:,.2f}%")
        print("[incrementality] method: descriptive pre/post, not causal ITS")
    print(f"[incrementality] → {out}")


if __name__ == "__main__":
    main()