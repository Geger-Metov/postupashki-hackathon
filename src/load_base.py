import pandas as pd
from sqlalchemy import text
from src.db import engine

EXCEL_PATH = "data/base.xlsx"

COLUMN_MAP = {
    "Номер студента": "student_id",
    "Сумма": "amount",
    "Курс": "course",
    "Время": "timestamp",
}

def load_and_validate(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)

    # Переименовываем колонки в английские
    df = df.rename(columns=COLUMN_MAP)

    print("=== INFO ===")
    print(df.info())

    print("\n=== ПРОПУСКИ ===")
    print(df.isna().sum())

    print("\n=== ДУБЛИ ===")
    print("Полных дублей:", df.duplicated().sum())

    print("\n=== ОТРИЦАТЕЛЬНЫЕ СУММЫ ===")
    print(df[df["amount"] < 0])

    # Приведение типов
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["student_id"] = df["student_id"].astype(str)
    df["course"] = df["course"].astype(str)

    # Удаляем полные дубли (осторожно: лучше логировать, а не молча)
    df = df.drop_duplicates()

    # order_id: группируем покупки одного пользователя в один момент времени
    # Это предположение: одновременные покупки = один заказ.
    df["order_id"] = df.groupby(["student_id", "timestamp"]).ngroup()

    return df


def load_to_postgres(df: pd.DataFrame):
    with engine.begin() as conn:
        # Сырая таблица
        df.to_sql("sales_raw", conn, if_exists="replace", index=False)

        # Очищенная таблица (пока та же, но можно отличать)
        df.to_sql("sales_clean", conn, if_exists="replace", index=False)

        # Индексы
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sales_student ON sales_clean(student_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sales_timestamp ON sales_clean(timestamp);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sales_course ON sales_clean(course);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sales_order ON sales_clean(order_id);"))

    print(f"Загружено строк: {len(df)}")


if __name__ == "__main__":
    df = load_and_validate(EXCEL_PATH)
    load_to_postgres(df)