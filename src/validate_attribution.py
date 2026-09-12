"""
Валидация attribution engine против ground truth.

Использует синтетическую воронку из src.generate_funnel:
    data/synthetic/attribution_results.csv   (результат src.attribution)
    data/synthetic/ground_truth.csv          (истинный placement каждого заказа)

Проверки:
    1. last_touch accuracy = 100% (в этой синтетике касания одного
       пользователя идут от одного placement).
    2. Reconciliation: сумма attributed_revenue по order_id = order_amount.
    3. Organic share по моделям.

Запуск:
    python -m src.validate_attribution --data-dir data/synthetic
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger("validate")


def check_last_touch_accuracy(
    attribution: pd.DataFrame, truth: pd.DataFrame
) -> float:
    lt = attribution[attribution["model"] == "last_touch"].copy()
    lt = lt[lt["placement_id"].notna()]

    merged = lt.merge(
        truth[["order_id", "placement_id"]],
        on="order_id",
        suffixes=("_attr", "_truth"),
    )
    if merged.empty:
        return float("nan")

    return float((merged["placement_id_attr"] == merged["placement_id_truth"]).mean())


def check_reconciliation(attribution: pd.DataFrame) -> pd.DataFrame:
    df = attribution[attribution["source_type"] != "organic"]
    if df.empty:
        return pd.DataFrame(columns=["attributed", "amount", "diff"])

    grp = df.groupby(["model", "order_id"]).agg(
        attributed=("attributed_revenue", "sum"),
        amount=("order_amount", "first"),
    )
    grp["diff"] = (grp["attributed"] - grp["amount"]).abs()
    return grp


def check_organic_share(attribution: pd.DataFrame) -> pd.Series:
    return (
        attribution.assign(is_organic=attribution["source_type"] == "organic")
        .groupby("model")["is_organic"]
        .mean()
    )


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=Path("data/synthetic"))
    ap.add_argument("--attribution", type=Path, default=None)
    ap.add_argument("--ground-truth", type=Path, default=None)
    args = ap.parse_args(argv)

    attribution_path = args.attribution or (args.data_dir / "attribution_results.csv")
    truth_path = args.ground_truth or (args.data_dir / "ground_truth.csv")

    attribution = pd.read_csv(attribution_path)
    truth = pd.read_csv(truth_path)

    log.info("attribution rows: %d", len(attribution))
    log.info("ground truth rows: %d", len(truth))

    # --- 1. last_touch accuracy ---
    acc = check_last_touch_accuracy(attribution, truth)
    log.info("last_touch accuracy: %.1f%%", acc * 100)
    if acc < 0.99:
        log.warning("last_touch accuracy < 99%% — проверьте attribution engine")

    # --- 2. reconciliation ---
    recon = check_reconciliation(attribution)
    if not recon.empty:
        max_diff = float(recon["diff"].max())
        log.info("reconciliation max |attributed - amount| = %.6f", max_diff)
        if max_diff > 1e-6:
            log.warning("reconciliation FAILED")

    # --- 3. organic share ---
    org = check_organic_share(attribution)
    log.info("organic share by model:\n%s", org.to_string())


if __name__ == "__main__":
    main()
