from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA = Path("data")


def build_sales_daily(orders: pd.DataFrame) -> pd.DataFrame:
    orders = orders.copy()
    orders["timestamp"] = pd.to_datetime(orders["timestamp"])
    orders["date"] = orders["timestamp"].dt.date
    return (
        orders.groupby("date", as_index=False)
        .agg(
            revenue=("total_amount", "sum"),
            orders=("order_id", "nunique"),
            unique_buyers=("student_id", "nunique"),
        )
        .sort_values("date")
    )


def build_posts_daily(posts: pd.DataFrame) -> pd.DataFrame:
    posts = posts.copy()
    posts["date"] = pd.to_datetime(posts["date"]).dt.date
    return (
        posts.groupby("date", as_index=False)
        .agg(posts=("post_id", "count"))
        .sort_values("date")
    )


def main() -> None:
    orders_path = DATA / "orders.csv"
    posts_path = DATA / "posts_postypashki_old.csv"

    if not orders_path.exists():
        raise FileNotFoundError(f"{orders_path} — сначала запусти normalize_sales.")
    if not posts_path.exists():
        raise FileNotFoundError(f"{posts_path} — файл постов не найден.")

    orders = pd.read_csv(orders_path, parse_dates=["timestamp"])
    posts = pd.read_csv(posts_path)

    sales_daily = build_sales_daily(orders)
    posts_daily = build_posts_daily(posts)

    merged = sales_daily.merge(posts_daily, on="date", how="outer")
    merged["revenue"] = merged["revenue"].fillna(0.0)
    merged["orders"] = merged["orders"].fillna(0).astype(int)
    merged["unique_buyers"] = merged["unique_buyers"].fillna(0).astype(int)
    merged["posts"] = merged["posts"].fillna(0).astype(int)
    merged = merged.sort_values("date").reset_index(drop=True)

    out = DATA / "sales_posts_daily.csv"
    merged.to_csv(out, index=False)
    print(f"[join] → {out}")
    print(merged.to_string(index=False))


if __name__ == "__main__":
    main()