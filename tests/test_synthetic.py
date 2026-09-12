"""Минимальные тесты для синтетики.

Запуск:
    python -m pytest tests/ -v
"""
from pathlib import Path

import pandas as pd


DATA = Path("data")


def test_ad_registry_exists():
    assert (DATA / "ad_registry.csv").exists(), "ad_registry.csv не создан"


def test_touches_exists():
    assert (DATA / "touches.csv").exists(), "touches.csv не создан"


def test_ad_registry_columns():
    df = pd.read_csv(DATA / "ad_registry.csv")
    required = {"placement_id", "campaign_id", "channel_id", "channel_name",
                "creative_id", "cost", "publication_time", "data_source"}
    assert required.issubset(df.columns), f"нет колонок: {required - set(df.columns)}"


def test_touches_columns():
    df = pd.read_csv(DATA / "touches.csv")
    required = {"touch_id", "user_id", "touch_type", "campaign_id",
                "placement_id", "creative_id", "timestamp", "start_param",
                "data_source"}
    assert required.issubset(df.columns)


def test_touch_types():
    df = pd.read_csv(DATA / "touches.csv")
    types = set(df["touch_type"].unique())
    assert types.issubset({"click", "bot_start", "lead"})


def test_data_source_marked():
    df = pd.read_csv(DATA / "touches.csv")
    assert (df["data_source"] == "synthetic").all()


def test_no_duplicates():
    df = pd.read_csv(DATA / "touches.csv")
    assert df["touch_id"].is_unique


def test_start_param_format():
    df = pd.read_csv(DATA / "touches.csv")
    sample = df["start_param"].iloc[0]
    assert sample.startswith("c_"), f"start_param = {sample}"
    assert "_p_" in sample
    assert "_cr_" in sample