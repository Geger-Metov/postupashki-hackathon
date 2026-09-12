from __future__ import annotations

import pandas as pd

from src.incrementality import pre_post_analysis
from src.join_sales_posts import build_sales_daily
from src.tracking_utils import parse_start_param

from src.attribution import (
    AttributionConfig,
    reconciliation,
    run_attribution,
)


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

def test_attribution_reconciles_revenue():

    touches = pd.DataFrame({
        "touch_id": ["t1", "t2"],
        "user_id": ["u1", "u1"],
        "touch_type": ["click", "lead"],
        "campaign_id": ["cmp1", "cmp1"],
        "placement_id": ["pl1", "pl2"],
        "creative_id": ["cr1", "cr2"],
        "timestamp": pd.to_datetime([
            "2026-08-01 10:00",
            "2026-08-03 10:00",
        ]),
        "data_source": ["synthetic", "synthetic"],
    })

    orders = pd.DataFrame({
        "order_id": ["o1", "o2"],
        "student_id": ["u1", "u2"],
        "total_amount": [1000.0, 500.0],
        "timestamp": pd.to_datetime([
            "2026-08-04 10:00",
            "2026-08-04 10:00",
        ]),
    })

    result = run_attribution(
        touches,
        orders,
        AttributionConfig(),
    )

    recon = reconciliation(result)

    assert recon["diff"].max() < 1e-6