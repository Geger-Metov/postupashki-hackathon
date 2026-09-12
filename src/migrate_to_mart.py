from __future__ import annotations

from pathlib import Path
import pandas as pd

from src.db import engine
from src.models import Base


DATA = Path("data")


def migrate() -> None:
    orders_path = DATA / "orders.csv"
    items_path = DATA / "order_items.csv"

    if not orders_path.exists() or not items_path.exists():
        raise FileNotFoundError(
            "Нет orders.csv/order_items.csv. Сначала запусти normalize_sales."
        )

    orders = pd.read_csv(orders_path, parse_dates=["timestamp"])
    items = pd.read_csv(items_path, parse_dates=["timestamp"])

    Base.metadata.create_all(engine)

    users = (
        orders[["student_id"]]
        .drop_duplicates()
        .rename(columns={"student_id": "user_id"})
    )
    users["source"] = "sales"
    users["hash"] = users["user_id"]
    users["first_seen_at"] = (
        orders.groupby("student_id")["timestamp"].min()
        .reindex(users["user_id"])
        .to_numpy()
    )

    courses = (
        items[["course"]]
        .drop_duplicates()
        .rename(columns={"course": "name"})
    )

    order_rows = orders.rename(
        columns={
            "student_id": "user_id",
            "timestamp": "created_at",
        }
    )[["order_id", "user_id", "created_at", "total_amount"]]

    with engine.begin() as conn:
        users.to_sql("users", conn, if_exists="append", index=False)
        courses.to_sql("courses", conn, if_exists="append", index=False)
        order_rows.to_sql("orders", conn, if_exists="append", index=False)

        course_map = pd.read_sql(
            "SELECT course_id, name FROM courses",
            conn,
        )
        course_map = dict(zip(course_map["name"], course_map["course_id"]))

        payments = items.rename(columns={"student_id": "user_id"}).copy()
        payments["course_id"] = payments["course"].map(course_map)
        payments = payments.rename(columns={"timestamp": "timestamp"})
        payments = payments[
            ["user_id", "order_id", "amount", "course_id", "timestamp"]
        ]
        payments.to_sql("payments", conn, if_exists="append", index=False)

    print(f"users:    {len(users)}")
    print(f"courses:  {len(courses)}")
    print(f"orders:   {len(order_rows)}")
    print(f"payments: {len(items)}")


if __name__ == "__main__":
    migrate()
