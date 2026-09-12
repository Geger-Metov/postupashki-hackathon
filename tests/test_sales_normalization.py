"""Тесты нормализации sales layer.

Запуск из корня проекта:
    python -m pytest tests/ -v
"""

from pathlib import Path

import pandas as pd
import pytest

from src.normalize_sales import (
    build_daily_metrics,
    build_order_items,
    build_orders,
    load_sales,
    make_order_id,
    normalize_sales,
)


DATA = Path("data")


def test_make_order_id_is_deterministic():
    ts = pd.Timestamp("2026-08-04 10:14:38")
    assert make_order_id("443", ts) == make_order_id("443", ts)
    assert make_order_id("443", ts) != make_order_id("444", ts)


def test_base_has_expected_shape():
    sales = load_sales(DATA / "base.xlsx")
    assert len(sales) == 795
    assert sales["student_id"].nunique() == 606


def test_order_items_preserve_source_rows():
    sales = load_sales(DATA / "base.xlsx")
    items = build_order_items(sales)
    assert len(items) == len(sales) == 795


def test_orders_are_grouped_by_student_and_timestamp():
    sales = load_sales(DATA / "base.xlsx")
    items = build_order_items(sales)
    orders = build_orders(items)
    assert len(orders) == 628
    assert orders["order_id"].is_unique


def test_bundle_definition():
    sales = load_sales(DATA / "base.xlsx")
    items = build_order_items(sales)
    orders = build_orders(items)
    assert int(orders["is_bundle"].sum()) == 153
    assert (orders["is_bundle"] == (orders["items_count"] >= 2)).all()


def test_repeat_purchase_is_order_level():
    sales = load_sales(DATA / "base.xlsx")
    items = build_order_items(sales)
    orders = build_orders(items)

    first_orders = orders.groupby("student_id")["timestamp"].idxmin()
    assert not orders.loc[first_orders, "is_repeat"].any()
    assert (orders["is_repeat"] == orders["previous_order_id"].notna()).all()


def test_revenue_is_conserved():
    sales = load_sales(DATA / "base.xlsx")
    items = build_order_items(sales)
    orders = build_orders(items)
    daily = build_daily_metrics(orders, items)

    expected = round(float(sales["amount"].sum()), 2)
    assert round(float(items["amount"].sum()), 2) == expected
    assert round(float(orders["total_amount"].sum()), 2) == expected
    assert round(float(daily["revenue"].sum()), 2) == expected


def test_items_count_is_conserved():
    sales = load_sales(DATA / "base.xlsx")
    items = build_order_items(sales)
    orders = build_orders(items)
    assert int(orders["items_count"].sum()) == len(items) == 795


def test_daily_metrics_have_no_duplicate_dates():
    sales = load_sales(DATA / "base.xlsx")
    items = build_order_items(sales)
    orders = build_orders(items)
    daily = build_daily_metrics(orders, items)
    assert daily["date"].is_unique


def test_normalize_sales_writes_three_outputs(tmp_path):
    orders, items, daily = normalize_sales(
        input_path=DATA / "base.xlsx",
        output_dir=tmp_path,
    )
    assert len(orders) == 628
    assert len(items) == 795
    assert len(daily) > 0
    assert (tmp_path / "orders.csv").exists()
    assert (tmp_path / "order_items.csv").exists()
    assert (tmp_path / "daily_metrics.csv").exists()
