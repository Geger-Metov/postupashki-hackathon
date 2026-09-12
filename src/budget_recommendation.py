from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def recommend_budget(
    romi_path: Path,
    budget: float,
) -> pd.DataFrame:

    df = pd.read_csv(romi_path)

    df = df[df["cost"] > 0].copy()

    df["recommendation"] = "test"

    df.loc[df["romi"] >= 1.0, "recommendation"] = "scale"
    df.loc[
        (df["romi"] >= 0) & (df["romi"] < 1.0),
        "recommendation",
    ] = "maintain"
    df.loc[df["romi"] < 0, "recommendation"] = "reduce"

    scale = df[df["recommendation"] == "scale"].copy()

    if scale.empty:
        scale = df.sort_values("romi", ascending=False).head(3).copy()

    # 70% proven placements
    scale_budget = budget * 0.70

    scale["recommended_budget"] = (
        scale["romi"].clip(lower=0) / scale["romi"].clip(lower=0).sum()
        * scale_budget
    )

    # Remaining budget:
    # 20% tests, 10% reserve.
    result = scale[
        [
            "placement_id",
            "campaign_id",
            "cost",
            "attributed_revenue",
            "romi",
            "roas",
            "recommendation",
            "recommended_budget",
        ]
    ].copy()

    return result.sort_values(
        "recommended_budget",
        ascending=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--romi",
        default="data/romi_by_placement.csv",
    )

    parser.add_argument(
        "--budget",
        type=float,
        default=300_000,
    )

    parser.add_argument(
        "--output",
        default="data/budget_recommendation.csv",
    )

    args = parser.parse_args()

    result = recommend_budget(
        Path(args.romi),
        args.budget,
    )

    result.to_csv(args.output, index=False)

    print(
        f"\nBudget recommendation for "
        f"{args.budget:,.0f} ₽:\n"
    )

    print(result.to_string(index=False))


if __name__ == "__main__":
    main()