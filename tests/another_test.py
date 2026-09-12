from __future__ import annotations

import pandas as pd

from src.incrementality import pre_post_analysis
from src.join_sales_posts import build_sales_daily
from src.tracking_bot import parse_start_param


def test_tracking_parser_preserves_string_ids():
    result = parse_start_param("c_cmp_2_p_pl_05_cr_cr_4")
    assert result == {
        "campaign_id": "cmp_2",
        "placement_id": "pl_05",
        "creative_id": "cr_4",
    }


def test_tracking_parser_rejects_invalid_value():
    result = parse_start_param("not-a-valid-param")
    assert result == {
        "campaign_id": None,
        "placement_id": None,
        "creative_id": None,
    }


def test_sales_daily_counts_orders_not_buyers():
    orders = pd.DataFrame(
        {
            "order_id": ["ord_a", "ord_b", "ord_c"],
            "student_id": ["s1", "s1", "s2"],
            "timestamp": pd.to_datetime(
                ["2026-08-01 10:00", "2026-08-01 12:00", "2026-08-01 13:00"]
            ),
            "total_amount": [100.0, 200.0, 300.0],
        }
    )
    daily = build_sales_daily(orders)
    assert daily.loc[0, "orders"] == 3
    assert daily.loc[0, "unique_buyers"] == 2
    assert daily.loc[0, "revenue"] == 600.0


def test_pre_post_analysis_uses_total_amount():
    dates = pd.date_range("2026-08-01", periods=4, freq="D")
    daily = pd.DataFrame(
        {
            "date": dates,
            "revenue": [100.0, 100.0, 200.0, 200.0],
        }
    )
    result = pre_post_analysis(daily, "2026-08-03", window_days=2)
    assert result["status"] == "ok"
    assert result["pre_avg_revenue"] == 100.0
    assert result["post_avg_revenue"] == 200.0
    assert result["lift_pct"] == 100.0
    assert result["method"] == "pre_post_descriptive"
