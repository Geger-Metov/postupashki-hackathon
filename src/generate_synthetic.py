"""Синтетика: ad_registry.csv + touches.csv.

ВАЖНО: user_id в touches берётся из data/identity_map.csv
(telegram_user_id = str(student_id)).

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


def _load_user_pool(identity_path: Path) -> list[str]:
    """Берём user_id из identity_map — это telegram_user_id (mock)."""
    if not identity_path.exists():
        raise FileNotFoundError(
            f"{identity_path} — нет. Запусти src.build_identity_map первым."
        )
    df = pd.read_csv(identity_path)
    return df["telegram_user_id"].astype(str).tolist()


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

    cost_levels = [25_000, 35_000, 45_000, 55_000, 70_000]
    quality_levels = ["strong", "medium", "weak"]
    quality_p = [0.2, 0.5, 0.3]

    rows = []
    for i in range(n):
        ch = channels.iloc[int(rng.integers(0, len(channels)))]
        cmp_ = campaigns.iloc[int(rng.integers(0, len(campaigns)))]
        cr = creatives.iloc[int(rng.integers(0, len(creatives)))]
        quality = str(rng.choice(quality_levels, p=quality_p))

        rows.append({
            "placement_id":   f"pl_{i:02d}",
            "campaign_id":    cmp_["campaign_id"],
            "channel_id":     ch["channel_id"],
            "channel_name":   ch["channel_name"],
            "creative_id":    cr["creative_id"],
            "cost":           float(rng.choice(cost_levels)),
            "publication_time": s + pd.Timedelta(seconds=float(rng.uniform(0, span))),
            "expected_quality": quality,
            "data_source":    "synthetic",
        })
    return pd.DataFrame(rows)


def generate_touches(
    placements: pd.DataFrame,
    user_pool: list[str],
    cfg: dict,
    rng: np.random.Generator,
) -> pd.DataFrame:
    s, e = _dates(cfg)
    span = (e - s).total_seconds()
    p_conv = cfg["synthetic"]["conversion_rate"]
    p_lead = cfg["synthetic"]["lead_rate"]

    # Касания зависят от quality placement
    quality_lambda = {"strong": 2.5, "medium": 1.5, "weak": 0.7}

    rows = []
    tid = 0

    for user_id in user_pool:
        n = int(np.clip(rng.poisson(1.5), 1, 5))
        idxs = rng.integers(0, len(placements), size=n)

        for idx in idxs:
            pl = placements.iloc[int(idx)]
            quality = pl.get("expected_quality", "medium")
            # вероятность клика по данному placement
            if rng.random() > min(quality_lambda[quality] / 3.0, 1.0):
                continue

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

    if not rows:
        return pd.DataFrame(columns=[
            "touch_id", "user_id", "touch_type", "campaign_id",
            "placement_id", "creative_id", "timestamp", "start_param", "data_source",
        ])

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

    user_pool = _load_user_pool(out / "identity_map.csv")

    channels = generate_channels(cfg["synthetic"]["n_channels"], rng)
    campaigns = generate_campaigns(cfg["synthetic"]["n_campaigns"], cfg)
    creatives = generate_creatives(cfg["synthetic"]["n_creatives"], rng)
    placements = generate_placements(
        cfg["synthetic"]["n_placements"], channels, campaigns, creatives, cfg, rng
    )
    touches = generate_touches(placements, user_pool, cfg, rng)

    placements.to_csv(out / "ad_registry.csv", index=False)
    touches.to_csv(out / "touches.csv", index=False)

    print(f"[synthetic] seed={seed}")
    print(f"[synthetic] user_pool size: {len(user_pool)}")
    print(f"[synthetic] placements: {len(placements)} → data/ad_registry.csv")
    print(f"[synthetic] touches:    {len(touches)} → data/touches.csv")
    if len(touches) > 0:
        print(f"[synthetic]   by type: {touches['touch_type'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()