"""ROMI: (Attributed Revenue − Cost) / Cost.

Запуск:
    python -m src.romi
Читает:  data/attribution_results.csv, data/ad_registry.csv
Пишет:   data/romi_by_campaign.csv, data/romi_by_placement.csv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path("data")


def _agg_attr(attr: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    return (
        attr.groupby(keys + ["model"], dropna=False)
        .agg(
            attributed_revenue=("attributed_revenue", "sum"),
            orders_count=("order_id", "nunique"),
        )
        .reset_index()
    )


def _safe_romi(revenue: pd.Series, cost: pd.Series) -> pd.Series:
    revenue = pd.to_numeric(revenue, errors="coerce").astype(float)
    cost = pd.to_numeric(cost, errors="coerce").astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        romi = (revenue - cost) / cost
    return romi.replace([np.inf, -np.inf], np.nan)


def compute_romi(attr: pd.DataFrame, reg: pd.DataFrame, level: str) -> pd.DataFrame:
    if level == "campaign":
        agg = _agg_attr(attr, ["campaign_id"])
        cost = reg.groupby("campaign_id", dropna=False)["cost"].sum().reset_index()
        out = agg.merge(cost, on="campaign_id", how="left")
        out["romi_attr"] = _safe_romi(out["attributed_revenue"], out["cost"])
        out["romi_inc"] = np.nan
        cols = ["campaign_id", "model", "attributed_revenue", "cost",
                "romi_attr", "romi_inc", "orders_count"]
        return out[cols].sort_values(["model", "attributed_revenue"],
                                     ascending=[True, False])

    if level == "placement":
        agg = _agg_attr(attr, ["placement_id"])
        meta = (
            reg.groupby(["placement_id", "campaign_id", "channel_name"], dropna=False)
            ["cost"].sum().reset_index()
        )
        out = agg.merge(meta, on="placement_id", how="left")
        out["romi_attr"] = _safe_romi(out["attributed_revenue"], out["cost"])
        out["romi_inc"] = np.nan
        cols = ["placement_id", "campaign_id", "channel_name", "model",
                "attributed_revenue", "cost", "romi_attr", "romi_inc", "orders_count"]
        return out[cols].sort_values(["model", "attributed_revenue"],
                                     ascending=[True, False])

    raise ValueError(f"Unknown level: {level}")


def main() -> None:
    attr_path = DATA / "attribution_results.csv"
    reg_path = DATA / "ad_registry.csv"

    if not attr_path.exists():
        raise FileNotFoundError(f"{attr_path} — нет. Ждём Разраба №1.")
    if not reg_path.exists():
        raise FileNotFoundError(f"{reg_path} — нет. Запусти generate_synthetic.")

    attr = pd.read_csv(attr_path)
    reg = pd.read_csv(reg_path)

    required = {"order_id", "campaign_id", "placement_id", "model", "attributed_revenue"}
    missing = required - set(attr.columns)
    if missing:
        raise ValueError(f"attribution_results.csv — нет колонок: {missing}")

    by_campaign = compute_romi(attr, reg, "campaign")
    by_placement = compute_romi(attr, reg, "placement")

    by_campaign.to_csv(DATA / "romi_by_campaign.csv", index=False)
    by_placement.to_csv(DATA / "romi_by_placement.csv", index=False)

    print(f"[romi] campaigns: {len(by_campaign)} → data/romi_by_campaign.csv")
    print(f"[romi] placements: {len(by_placement)} → data/romi_by_placement.csv")


if __name__ == "__main__":
    main()