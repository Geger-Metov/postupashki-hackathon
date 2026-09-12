"""
ROMI calculator.

Вход:
    data/attribution_results.csv   (из src.attribution)
    data/ad_registry.csv           (из src.generate_synthetic)

Выход:
    data/romi_by_placement.csv
    data/romi_by_campaign.csv

Формула:
    ROMI_attr = (attributed_revenue - cost) / cost

ASSUMPTION (критично):
    cost из ad_registry — синтетический. В реальности его надо
    собирать вручную (это часть measurement system на будущее).
    ROMI_inc (incremental) здесь НЕ считается — см. docs/romi.md.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger("romi")

DEFAULT_DATA_DIR = Path("data")


# --------------------------------------------------------------------------
# ROMI
# --------------------------------------------------------------------------

def romi_by_placement(
    attribution: pd.DataFrame,
    ad_registry: pd.DataFrame,
    model: str = "last_touch",
) -> pd.DataFrame:
    """
    ROMI по каждому placement для выбранной модели атрибуции.
    """
    df = attribution[attribution["model"] == model].copy()

    # стоимость показов: 1 placement = 1 строка в ad_registry
    cost = (
        ad_registry[["placement_id", "cost", "campaign_id", "channel_id",
                     "publication_time"]]
        .drop_duplicates("placement_id")
    )

    # приписанная выручка
    rev = (
        df[df["placement_id"].notna()]
        .groupby("placement_id")
        .agg(
            attributed_revenue=("attributed_revenue", "sum"),
            orders=("order_id", "nunique"),
            touches=("touch_id", "nunique"),
        )
        .reset_index()
    )

    merged = cost.merge(rev, on="placement_id", how="left").fillna({
        "attributed_revenue": 0.0,
        "orders": 0,
        "touches": 0,
    })

    merged["model"] = model
    merged["romi"] = np.where(
        merged["cost"] > 0,
        (merged["attributed_revenue"] - merged["cost"]) / merged["cost"],
        np.nan,
    )
    # сколько раз окупилось (для наглядности)
    merged["roas"] = np.where(
        merged["cost"] > 0,
        merged["attributed_revenue"] / merged["cost"],
        np.nan,
    )

    return merged.sort_values("romi", ascending=False).reset_index(drop=True)


def romi_by_campaign(
    romi_placement: pd.DataFrame,
) -> pd.DataFrame:
    """Агрегируем placement-level ROMI до кампании."""
    grp = (
        romi_placement.groupby(["model", "campaign_id"])
        .agg(
            cost=("cost", "sum"),
            attributed_revenue=("attributed_revenue", "sum"),
            placements=("placement_id", "nunique"),
            orders=("orders", "sum"),
            touches=("touches", "sum"),
        )
        .reset_index()
    )
    grp["romi"] = np.where(
        grp["cost"] > 0,
        (grp["attributed_revenue"] - grp["cost"]) / grp["cost"],
        np.nan,
    )
    grp["roas"] = np.where(
        grp["cost"] > 0,
        grp["attributed_revenue"] / grp["cost"],
        np.nan,
    )
    return grp.sort_values("romi", ascending=False).reset_index(drop=True)


def compare_models(
    attribution: pd.DataFrame,
    ad_registry: pd.DataFrame,
) -> pd.DataFrame:
    """ROMI по трём моделям — для сравнения (Задача 6)."""
    frames = []
    for model in attribution["model"].unique():
        frames.append(romi_by_placement(attribution, ad_registry, model))
    all_df = pd.concat(frames, ignore_index=True)
    return all_df[["model", "placement_id", "cost",
                   "attributed_revenue", "romi", "roas"]]


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="ROMI calculator")
    p.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    p.add_argument("--attribution", type=Path, default=None)
    p.add_argument("--ad-registry", type=Path, default=None)
    p.add_argument("--out-dir", type=Path, default=None)
    return p


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _build_argparser().parse_args(argv)

    data_dir = args.data_dir
    attribution_path = args.attribution or (data_dir / "attribution_results.csv")
    ad_registry_path = args.ad_registry or (data_dir / "ad_registry.csv")
    out_dir = args.out_dir or data_dir

    attribution = pd.read_csv(attribution_path)
    ad_registry = pd.read_csv(ad_registry_path)

    log.info("attribution: %d rows", len(attribution))
    log.info("ad_registry: %d placements, total cost = %.0f",
             len(ad_registry), ad_registry["cost"].sum())

    # --- placement-level, last_touch ---
    romi_pl = romi_by_placement(attribution, ad_registry, "last_touch")
    romi_pl.to_csv(out_dir / "romi_by_placement.csv", index=False)

    # --- campaign-level ---
    romi_cmp = romi_by_campaign(
        pd.concat(
            [romi_by_placement(attribution, ad_registry, m)
             for m in attribution["model"].unique()],
            ignore_index=True,
        )
    )
    romi_cmp.to_csv(out_dir / "romi_by_campaign.csv", index=False)

    # --- сравнение моделей ---
    cmp_df = compare_models(attribution, ad_registry)
    cmp_df.to_csv(out_dir / "romi_by_model.csv", index=False)

    # --- вывод ---
    log.info("\nTop-10 placements (last_touch):\n%s",
             romi_pl.head(10)[["placement_id", "cost",
                               "attributed_revenue", "romi", "roas"]]
             .to_string(index=False))

    log.info("\nBy campaign (last_touch):\n%s",
             romi_cmp[romi_cmp["model"] == "last_touch"]
             [["campaign_id", "cost", "attributed_revenue", "romi"]]
             .to_string(index=False))

    # --- сколько placements убыточны ---
    last_touch = romi_pl
    unprofitable = last_touch[last_touch["romi"] < 0]
    log.info("\nunprofitable placements (last_touch): %d / %d",
             len(unprofitable), len(last_touch))

    # --- общий ROMI ---
    total_cost = float(last_touch["cost"].sum())
    total_rev = float(last_touch["attributed_revenue"].sum())
    if total_cost > 0:
        total_romi = (total_rev - total_cost) / total_cost
        log.info("TOTAL ROMI (last_touch) = %.2f  (rev=%.0f, cost=%.0f)",
                 total_romi, total_rev, total_cost)

    log.info("\nWrote romi_by_placement.csv, romi_by_campaign.csv, romi_by_model.csv")


if __name__ == "__main__":
    main()
