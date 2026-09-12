"""Синтетика: ad_registry.csv + touches.csv.

Запуск:
    python -m src.generate_synthetic
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dates(cfg: dict) -> tuple[pd.Timestamp, pd.Timestamp]:
    return (
        pd.Timestamp(cfg["date_range"]["start"]),
        pd.Timestamp(cfg["date_range"]["end"]),
    )


def generate_channels(n: int, rng: np.random.Generator) -> pd.DataFrame:
    themes = rng.choice(["edu", "it", "marketing", "career"], size=n)
    return pd.DataFrame({
        "channel_id":   [f"ch_{i:02d}" for i in range(n)],
        "channel_name": [f"channel_{i:02d}" for i in range(n)],
        "theme":        themes,
    })


def generate_campaigns(n: int, cfg: dict) -> pd.DataFrame:
    courses = cfg["courses"]
    chosen = [courses[i % len(courses)] for i in range(n)]
    return pd.DataFrame({
        "campaign_id":   [f"cmp_{i}" for i in range(n)],
        "campaign_name": chosen,
    })


def generate_creatives(n: int, rng: np.random.Generator) -> pd.DataFrame:
    kinds = rng.choice(["video", "banner", "text"], size=n)
    return pd.DataFrame({
        "creative_id":   [f"cr_{i}" for i in range(n)],
        "creative_type": kinds,
    })


def generate_placements(
    n: int,
    channels: pd.DataFrame,
    campaigns: pd.DataFrame,
    creatives: pd.DataFrame,
    cfg: dict,
    rng: np.random.Generator,
) -> pd.DataFrame:
    s, e = _dates(cfg)
    span = (e - s).total_seconds()
    rows = []
    for i in range(n):
        ch = channels.iloc[int(rng.integers(0, len(channels)))]
        cmp_ = campaigns.iloc[int(rng.integers(0, len(campaigns)))]
        cr = creatives.iloc[int(rng.integers(0, len(creatives)))]
        rows.append({
            "placement_id":   f"pl_{i:02d}",
            "campaign_id":    cmp_["campaign_id"],
            "channel_id":     ch["channel_id"],
            "channel_name":   ch["channel_name"],
            "creative_id":    cr["creative_id"],
            "cost":           float(rng.integers(cfg["synthetic"]["cost_min"],
                                                 cfg["synthetic"]["cost_max"])),
            "publication_time": s + pd.Timedelta(seconds=float(rng.uniform(0, span))),
            "data_source":    "synthetic",
        })
    return pd.DataFrame(rows)


def generate_touches(
    placements: pd.DataFrame,
    cfg: dict,
    rng: np.random.Generator,
) -> pd.DataFrame:
    s, e = _dates(cfg)
    span = (e - s).total_seconds()
    n_users = cfg["synthetic"]["n_users"]
    mean_t = cfg["synthetic"]["touches_per_user_mean"]
    p_conv = cfg["synthetic"]["conversion_rate"]
    p_lead = cfg["synthetic"]["lead_rate"]

    rows = []
    tid = 0
    for u in range(n_users):
        user_id = f"u_{u:05d}"
        n = int(np.clip(rng.poisson(mean_t), 1, 5))
        for idx in rng.integers(0, len(placements), size=n):
            pl = placements.iloc[int(idx)]
            sp = f"c_{pl['campaign_id']}_p_{pl['placement_id']}_cr_{pl['creative_id']}"
            ts = s + pd.Timedelta(seconds=float(rng.uniform(0, span)))

            def emit(kind: str, when: pd.Timestamp) -> None:
                nonlocal tid
                rows.append({
                    "touch_id":    f"t_{tid:06d}",
                    "user_id":     user_id,
                    "touch_type":  kind,
                    "campaign_id": pl["campaign_id"],
                    "placement_id": pl["placement_id"],
                    "creative_id": pl["creative_id"],
                    "timestamp":   when,
                    "start_param": sp,
                    "data_source": "synthetic",
                })
                tid += 1

            emit("click", ts)
            if rng.random() < p_conv:
                ts2 = ts + pd.Timedelta(seconds=int(rng.integers(30, 3600)))
                emit("bot_start", ts2)
                if rng.random() < p_lead:
                    ts3 = ts2 + pd.Timedelta(minutes=int(rng.integers(1, 60)))
                    emit("lead", ts3)

    return pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--out-dir", default="data")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    seed = args.seed if args.seed is not None else cfg.get("seed", 42)
    rng = np.random.default_rng(seed)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    channels = generate_channels(cfg["synthetic"]["n_channels"], rng)
    campaigns = generate_campaigns(cfg["synthetic"]["n_campaigns"], cfg)
    creatives = generate_creatives(cfg["synthetic"]["n_creatives"], rng)
    placements = generate_placements(
        cfg["synthetic"]["n_placements"], channels, campaigns, creatives, cfg, rng
    )
    touches = generate_touches(placements, cfg, rng)

    placements.to_csv(out / "ad_registry.csv", index=False)
    touches.to_csv(out / "touches.csv", index=False)

    print(f"[synthetic] seed={seed}")
    print(f"[synthetic] placements: {len(placements)} → data/ad_registry.csv")
    print(f"[synthetic] touches:    {len(touches)} → data/touches.csv")
    print(f"[synthetic]   by type: {touches['touch_type'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()