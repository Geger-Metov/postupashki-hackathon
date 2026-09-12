"""
Stage 3: полный синтетический funnel.

    placement → click → bot_start → lead → synthetic order

Запуск:
    python -m src.generate_funnel

Outputs (в data/synthetic/):
    ad_registry.csv    — 30 placements с cost и publication_time
    users.csv          — 1000 synthetic users
    touches.csv        — click / bot_start / lead события
    orders.csv         — 100+ synthetic orders
    ground_truth.csv   — какой placement реально привёл к заказу

Зачем:
    1. Attribution можно проверить против известного правильного ответа.
    2. Есть полная цепочка marketing activity → touch → payment.
    3. ROMI считается на данных, где мы контролируем всё.

ОТЛИЧИЕ от src/generate_synthetic.py:
    generate_synthetic.py — mock-stitch touches на РЕАЛЬНЫЕ orders.
                            Нужен для демонстрации attribution на реальных
                            данных, но ground truth отсутствует.
    generate_funnel.py    — полностью синтетическая воронка с ground truth.
                            Нужен для ВАЛИДАЦИИ attribution engine.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

log = logging.getLogger("generate_funnel")


# --------------------------------------------------------------------------
# Конфиг
# --------------------------------------------------------------------------

def load_config(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# --------------------------------------------------------------------------
# Справочники
# --------------------------------------------------------------------------

def build_ad_registry(cfg: dict, rng: np.random.Generator) -> pd.DataFrame:
    n_channels = 10
    n_campaigns = 8
    n_creatives = 15
    n_placements = 30

    channels = [f"ch_{i:03d}" for i in range(n_channels)]
    campaigns = [f"cmp_{i:03d}" for i in range(n_campaigns)]
    creatives = [f"cr_{i:03d}" for i in range(n_creatives)]

    s = pd.Timestamp(cfg["date_range"]["start"])
    e = pd.Timestamp(cfg["date_range"]["end"])
    span = (e - s).total_seconds()

    rows = []
    for i in range(n_placements):
        rows.append({
            "placement_id": f"pl_{i:03d}",
            "campaign_id": campaigns[i % n_campaigns],
            "channel_id": channels[i % n_channels],
            "creative_id": creatives[i % n_creatives],
            "cost": float(rng.integers(3000, 40000)),
            "publication_time": s + pd.Timedelta(seconds=float(rng.uniform(0, span))),
            "data_source": "synthetic",
        })
    return pd.DataFrame(rows)


def build_users(n: int, cfg: dict, rng: np.random.Generator) -> pd.DataFrame:
    s = pd.Timestamp(cfg["date_range"]["start"])
    e = pd.Timestamp(cfg["date_range"]["end"])
    span = (e - s).total_seconds()
    return pd.DataFrame({
        "user_id": [f"su_{i:05d}" for i in range(n)],
        "created_at": s + pd.to_timedelta(rng.uniform(0, span, size=n), unit="s"),
        "data_source": "synthetic",
    })


# --------------------------------------------------------------------------
# Воронка
# --------------------------------------------------------------------------

def _touch_row(tid: int, user_id: str, pl: pd.Series,
               source_type: str, ts: pd.Timestamp) -> dict:
    return {
        "touch_id": f"st_{tid:06d}",
        "user_id": user_id,
        "campaign_id": pl["campaign_id"],
        "placement_id": pl["placement_id"],
        "creative_id": pl["creative_id"],
        "source_type": source_type,
        "timestamp": ts,
        "start_param": (
            f"c_{pl['campaign_id']}_p_{pl['placement_id']}_cr_{pl['creative_id']}"
        ),
        "data_source": "synthetic",
    }


def simulate_funnel(
    users: pd.DataFrame,
    placements: pd.DataFrame,
    cfg: dict,
    rng: np.random.Generator,
    window_days: int = 7,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Прогоняем каждого пользователя через воронку.

    Вероятности подобраны так, чтобы из 1000 users получалось
    ~130-150 orders (>100 с запасом).
    """
    # Качество каждого placement влияет на CTR. Держим отдельно,
    # чтобы не пачкать ad_registry.
    quality = {pl: float(rng.beta(2, 5)) for pl in placements["placement_id"]}

    courses = cfg.get("courses", ["course_a", "course_b", "course_c"])
    prices = [3990.0, 5990.0, 9990.0, 14990.0, 19990.0]

    touches: list[dict] = []
    orders: list[dict] = []
    truth: list[dict] = []
    tid = 0
    oid = 0

    stats = {"exposed": 0, "click": 0, "bot_start": 0, "lead": 0, "order": 0}

    for _, user in users.iterrows():
        # 15% — органика, без рекламного касания и без заказа.
        # (Для MVP этого достаточно; в реальности часть органики
        #  всё равно покупает, но нам сейчас важна ad-driven цепочка.)
        if rng.random() < 0.15:
            continue

        pl = placements.iloc[int(rng.integers(0, len(placements)))]
        pub = pd.Timestamp(pl["publication_time"])

        # Пользователь входит в воронку через 0.5-72 часа после публикации.
        t0 = pub + pd.Timedelta(hours=float(rng.uniform(0.5, 72)))
        stats["exposed"] += 1

        # --- click ---
        p_click = 0.4 + 0.4 * quality[pl["placement_id"]]  # ~[0.4, 0.8]
        if rng.random() > p_click:
            continue
        touches.append(_touch_row(tid, user["user_id"], pl, "click", t0))
        tid += 1
        stats["click"] += 1

        # --- bot_start ---
        t1 = t0 + pd.Timedelta(minutes=float(rng.uniform(1, 30)))
        if rng.random() > 0.7:
            continue
        touches.append(_touch_row(tid, user["user_id"], pl, "bot_start", t1))
        tid += 1
        stats["bot_start"] += 1

        # --- lead ---
        t2 = t1 + pd.Timedelta(hours=float(rng.uniform(0.5, 24)))
        if rng.random() > 0.65:
            continue
        touches.append(_touch_row(tid, user["user_id"], pl, "lead", t2))
        tid += 1
        stats["lead"] += 1

        # --- order ---
        # Должен попасть в окно window_days от lead.
        t3 = t2 + pd.Timedelta(hours=float(rng.uniform(1, window_days * 24 - 1)))
        if rng.random() > 0.7:
            continue
        order_id = f"so_{oid:05d}"
        orders.append({
            "order_id": order_id,
            "user_id": user["user_id"],
            "total_amount": float(rng.choice(prices)),
            "course": str(rng.choice(courses)),
            "timestamp": t3,
            "data_source": "synthetic",
        })
        truth.append({
            "order_id": order_id,
            "user_id": user["user_id"],
            "placement_id": pl["placement_id"],
            "campaign_id": pl["campaign_id"],
            "channel_id": pl["channel_id"],
            "click_timestamp": t0,
            "order_timestamp": t3,
        })
        oid += 1
        stats["order"] += 1

    log.info("funnel stats: %s", stats)

    return (
        pd.DataFrame(touches),
        pd.DataFrame(orders),
        pd.DataFrame(truth),
    )


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description="Stage 3: synthetic funnel")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--out-dir", default="data/synthetic")
    ap.add_argument("--n-users", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--window-days", type=int, default=7)
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    seed = args.seed if args.seed is not None else cfg.get("seed", 42)
    rng = np.random.default_rng(seed)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    log.info("seed=%s, n_users=%s, window=%sd", seed, args.n_users, args.window_days)

    ad_registry = build_ad_registry(cfg, rng)
    users = build_users(args.n_users, cfg, rng)
    touches, orders, truth = simulate_funnel(
        users, ad_registry, cfg, rng, args.window_days,
    )

    ad_registry.to_csv(out / "ad_registry.csv", index=False)
    users.to_csv(out / "users.csv", index=False)
    touches.to_csv(out / "touches.csv", index=False)
    orders.to_csv(out / "orders.csv", index=False)
    truth.to_csv(out / "ground_truth.csv", index=False)

    log.info("users:    %d → %s", len(users), out / "users.csv")
    log.info("touches:  %d → %s", len(touches), out / "touches.csv")
    log.info("orders:   %d → %s", len(orders), out / "orders.csv")
    log.info("truth:    %d → %s", len(truth), out / "ground_truth.csv")
    log.info("placements: %d → %s", len(ad_registry), out / "ad_registry.csv")

    if len(orders) < 100:
        log.warning(
            "orders < 100. Увеличьте --n-users или ослабьте вероятности."
        )


if __name__ == "__main__":
    main()
