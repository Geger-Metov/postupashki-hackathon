"""Нормализация продаж из data/base.xlsx.

На выходе:
    data/orders.csv
    data/order_items.csv
    data/daily_metrics.csv

Определение заказа в рамках кейса:
    уникальная пара (student_id, timestamp).

Важно: base.xlsx не изменяется. Все преобразования выполняются в памяти,
а результаты сохраняются в отдельные CSV.

Запуск из корня проекта:
    python -m src.normalize_sales
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "base.xlsx"
DEFAULT_OUTPUT_DIR = ROOT / "data"

COLUMN_MAP = {
    "Номер студента": "student_id",
    "Сумма": "amount",
    "Курс": "course",
    "Время": "timestamp",
}

RAW_COLUMNS = ["student_id", "amount", "course", "timestamp"]
ORDER_COLUMNS = [
    "order_id",
    "student_id",
    "timestamp",
    "total_amount",
    "items_count",
    "is_bundle",
    "is_repeat",
    "previous_order_id",
    "days_since_previous_order",
]
ORDER_ITEM_COLUMNS = [
    "order_id",
    "item_index",
    "student_id",
    "timestamp",
    "course",
    "amount",
]
DAILY_COLUMNS = [
    "date",
    "orders_count",
    "unique_buyers",
    "revenue",
    "items_count",
    "average_order_value",
    "new_buyers",
    "repeat_orders",
    "bundle_orders",
]


class SalesDataError(ValueError):
    """Ошибка качества или структуры исходных продаж."""


def make_order_id(student_id: str, timestamp: pd.Timestamp) -> str:
    """Создать детерминированный ID заказа из его естественного ключа."""
    raw = f"{student_id}|{timestamp.isoformat()}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"ord_{digest}"


def load_sales(path: Path = DEFAULT_INPUT) -> pd.DataFrame:
    """Загрузить и провалидировать исходный base.xlsx."""
    if not path.exists():
        raise FileNotFoundError(f"Файл с продажами не найден: {path}")

    df = pd.read_excel(path)
    missing = set(COLUMN_MAP) - set(df.columns)
    if missing:
        raise SalesDataError(f"В base.xlsx отсутствуют колонки: {sorted(missing)}")

    df = df.rename(columns=COLUMN_MAP)[RAW_COLUMNS].copy()

    df["student_id"] = df["student_id"].astype("string")
    df["course"] = df["course"].astype("string")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    if df.isna().any().any():
        nulls = df.isna().sum()
        bad = nulls[nulls > 0].to_dict()
        raise SalesDataError(f"После приведения типов обнаружены пропуски: {bad}")

    if (df["amount"] < 0).any():
        bad_rows = df.loc[df["amount"] < 0]
        raise SalesDataError(
            f"Обнаружены отрицательные суммы: {len(bad_rows)} строк. "
            "На этом этапе мы их не исправляем автоматически."
        )

    # Полные дубли не удаляем молча: в исходном base.xlsx их сейчас нет.
    duplicate_count = int(df.duplicated().sum())
    if duplicate_count:
        raise SalesDataError(
            f"Обнаружены {duplicate_count} полных дублей. "
            "Сначала разберите их как проблему качества данных."
        )

    return df.sort_values(["student_id", "timestamp", "course"], kind="stable").reset_index(drop=True)


def build_order_items(sales: pd.DataFrame) -> pd.DataFrame:
    """Построить детализацию: одна строка = один курс внутри заказа."""
    items = sales.copy()
    items["order_id"] = [
        make_order_id(student_id, timestamp)
        for student_id, timestamp in zip(items["student_id"], items["timestamp"])
    ]

    # Порядок строк внутри заказа стабилен благодаря сортировке load_sales().
    items["item_index"] = items.groupby("order_id", sort=False).cumcount() + 1

    items = items[
        [
            "order_id",
            "item_index",
            "student_id",
            "timestamp",
            "course",
            "amount",
        ]
    ]
    return items[ORDER_ITEM_COLUMNS]


def build_orders(order_items: pd.DataFrame) -> pd.DataFrame:
    """Построить слой заказов: одна строка = один заказ."""
    grouped = (
        order_items.groupby(
            ["order_id", "student_id", "timestamp"],
            as_index=False,
            sort=False,
        )
        .agg(
            total_amount=("amount", "sum"),
            items_count=("course", "size"),
        )
    )

    grouped = grouped.sort_values(
        ["student_id", "timestamp", "order_id"], kind="stable"
    ).reset_index(drop=True)

    grouped["is_bundle"] = grouped["items_count"] >= 2

    # Повторная покупка — свойство заказа: у пользователя уже был предыдущий заказ.
    grouped["previous_order_id"] = grouped.groupby("student_id", sort=False)[
        "order_id"
    ].shift(1)
    grouped["is_repeat"] = grouped["previous_order_id"].notna()

    previous_timestamp = grouped.groupby("student_id", sort=False)["timestamp"].shift(1)
    grouped["days_since_previous_order"] = (
        (grouped["timestamp"] - previous_timestamp).dt.total_seconds() / 86400
    ).round(6)

    grouped["total_amount"] = grouped["total_amount"].round(2)
    grouped["items_count"] = grouped["items_count"].astype(int)

    return grouped[ORDER_COLUMNS]


def build_daily_metrics(orders: pd.DataFrame, order_items: pd.DataFrame) -> pd.DataFrame:
    """Построить дневные бизнес-метрики из нормализованных заказов."""
    orders = orders.copy()
    orders["date"] = orders["timestamp"].dt.date

    daily = (
        orders.groupby("date", as_index=False)
        .agg(
            orders_count=("order_id", "nunique"),
            unique_buyers=("student_id", "nunique"),
            revenue=("total_amount", "sum"),
        )
    )

    items_per_day = (
        order_items.assign(date=order_items["timestamp"].dt.date)
        .groupby("date", as_index=False)
        .agg(items_count=("order_id", "size"))
    )

    extras = (
        orders.groupby("date", as_index=False)
        .agg(
            repeat_orders=("is_repeat", "sum"),
            bundle_orders=("is_bundle", "sum"),
        )
    )

    # Новый покупатель = первый заказ данного student_id в доступной истории.
    first_order_date = orders.groupby("student_id")["timestamp"].transform("min").dt.date
    orders["is_new_buyer"] = orders["date"] == first_order_date
    new_buyers = (
        orders.loc[orders["is_new_buyer"]]
        .groupby("date", as_index=False)
        .agg(new_buyers=("student_id", "nunique"))
    )

    daily = daily.merge(items_per_day, on="date", how="left")
    daily = daily.merge(extras, on="date", how="left")
    daily = daily.merge(new_buyers, on="date", how="left")

    daily["new_buyers"] = daily["new_buyers"].fillna(0).astype(int)
    daily["repeat_orders"] = daily["repeat_orders"].astype(int)
    daily["bundle_orders"] = daily["bundle_orders"].astype(int)
    daily["items_count"] = daily["items_count"].astype(int)
    daily["average_order_value"] = (
        daily["revenue"] / daily["orders_count"]
    ).round(2)
    daily["revenue"] = daily["revenue"].round(2)

    return daily[DAILY_COLUMNS].sort_values("date").reset_index(drop=True)


def validate_outputs(
    sales: pd.DataFrame,
    orders: pd.DataFrame,
    order_items: pd.DataFrame,
    daily_metrics: pd.DataFrame,
) -> None:
    """Проверить ключевые инварианты нормализованного слоя."""
    if len(order_items) != len(sales):
        raise SalesDataError(
            f"order_items содержит {len(order_items)} строк вместо {len(sales)}."
        )

    if orders["order_id"].duplicated().any():
        raise SalesDataError("order_id не уникален в orders.csv.")

    if not order_items["order_id"].isin(orders["order_id"]).all():
        raise SalesDataError("В order_items есть order_id, отсутствующие в orders.")

    if orders["items_count"].sum() != len(order_items):
        raise SalesDataError("Сумма items_count не совпадает с числом order_items.")

    items_revenue = round(float(order_items["amount"].sum()), 2)
    orders_revenue = round(float(orders["total_amount"].sum()), 2)
    if items_revenue != orders_revenue:
        raise SalesDataError(
            f"Выручка не сходится: items={items_revenue}, orders={orders_revenue}."
        )

    daily_revenue = round(float(daily_metrics["revenue"].sum()), 2)
    if daily_revenue != orders_revenue:
        raise SalesDataError(
            f"Дневная выручка не сходится: daily={daily_revenue}, orders={orders_revenue}."
        )

    if orders["student_id"].nunique() != sales["student_id"].nunique():
        raise SalesDataError("Количество уникальных покупателей изменилось.")

    if int(orders["is_bundle"].sum()) != int((orders["items_count"] >= 2).sum()):
        raise SalesDataError("is_bundle не соответствует items_count.")

    # Первый заказ каждого покупателя не может быть repeat.
    first_orders = orders.groupby("student_id")["timestamp"].idxmin()
    if orders.loc[first_orders, "is_repeat"].any():
        raise SalesDataError("Первый заказ покупателя помечен как repeat.")


def normalize_sales(
    input_path: Path = DEFAULT_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Полный pipeline нормализации продаж."""
    sales = load_sales(input_path)
    order_items = build_order_items(sales)
    orders = build_orders(order_items)
    daily_metrics = build_daily_metrics(orders, order_items)

    validate_outputs(sales, orders, order_items, daily_metrics)

    output_dir.mkdir(parents=True, exist_ok=True)
    order_items.to_csv(output_dir / "order_items.csv", index=False)
    orders.to_csv(output_dir / "orders.csv", index=False)
    daily_metrics.to_csv(output_dir / "daily_metrics.csv", index=False)

    return orders, order_items, daily_metrics


def main() -> None:
    orders, order_items, daily_metrics = normalize_sales()

    print("=== SALES NORMALIZATION ===")
    print(f"Исходных строк:      {len(order_items)}")
    print(f"Заказов:             {len(orders)}")
    print(f"Уникальных покупателей: {orders['student_id'].nunique()}")
    print(f"Пакетных заказов:    {int(orders['is_bundle'].sum())}")
    print(f"Повторных заказов:   {int(orders['is_repeat'].sum())}")
    print(f"Выручка:             {orders['total_amount'].sum():,.2f} ₽")
    print(f"Дней:                {len(daily_metrics)}")
    print("\nСозданы:")
    print(f"  {DEFAULT_OUTPUT_DIR / 'orders.csv'}")
    print(f"  {DEFAULT_OUTPUT_DIR / 'order_items.csv'}")
    print(f"  {DEFAULT_OUTPUT_DIR / 'daily_metrics.csv'}")


if __name__ == "__main__":
    main()
