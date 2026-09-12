import pandas as pd
from src.db import engine
from src.models import Base


def migrate():
    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        # Читаем sales_clean
        df = pd.read_sql("SELECT * FROM sales_clean", conn)

        # 1. users
        users = (
            df[["student_id"]]
            .drop_duplicates()
            .rename(columns={"student_id": "user_id"})
        )
        users["user_id"] = users["user_id"].astype(int)
        users["source"] = None
        users["first_seen_at"] = None
        users.to_sql("users", conn, if_exists="append", index=False)

        # 2. courses
        courses = (
            df[["course"]]
            .drop_duplicates()
            .rename(columns={"course": "name"})
        )
        courses.to_sql("courses", conn, if_exists="append", index=False)

        # 3. orders — агрегат по order_id
        orders = (
            df.groupby("order_id")
            .agg(
                user_id=("student_id", "first"),
                created_at=("timestamp", "min"),
                total_amount=("amount", "sum"),
            )
            .reset_index()
        )
        orders.to_sql("orders", conn, if_exists="append", index=False)

        # 4. payments — по строке на покупку
        course_map = pd.read_sql("SELECT course_id, name FROM courses", conn)
        course_map = dict(zip(course_map["name"], course_map["course_id"]))

        payments = df.rename(columns={"student_id": "user_id"}).copy()
        payments["course_id"] = payments["course"].map(course_map)
        payments = payments[["user_id", "order_id", "amount", "course_id", "timestamp"]]
        payments.to_sql("payments", conn, if_exists="append", index=False)

        print(f"users:    {len(users)}")
        print(f"courses:  {len(courses)}")
        print(f"orders:   {len(orders)}")
        print(f"payments: {len(payments)}")


if __name__ == "__main__":
    migrate()