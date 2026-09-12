"""
Синтетика: ad_registry.csv + touches.csv.

Запуск:
    python -m src.generate_synthetic

КЛЮЧЕВОЕ ОТЛИЧИЕ ОТ ПРЕДЫДУЩЕЙ ВЕРСИИ:
    touches генерируются от реальных student_id из orders.csv,
    вокруг реальных дат покупок. Это делает возможным честный
    attribution: user_id в touches и student_id в orders — одно
    и то же пространство идентификаторов.

ASSUMPTION:
    Это MOCK-stitching. В реальности user_id (Telegram) и
    student_id (sales layer) — разные сущности, и связь между
    ними — часть будущей measurement system. Здесь мы
    искусственно приравниваем их для демонстрации механики.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


# --------------------------------------------------------------------------
# Конфиг
# --------------------------------------------------------------------------

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dates(cfg: dict) -> tuple[pd.Timestamp, pd.Timestamp]:
    return (
        pd.Timestamp(cfg["date_range"]["start"]),
        pd.Timestamp(cfg["date_range"]["end"]),
    )


# --------------------------------------------------------------------------
# Генерация справочников
# --------------------------------------------------------------------------

def generate_channels(n: int, rng: np.random.Generator) -> pd.DataFrame:
    themes = rng.choice(["edu", "it", "marketing", "career"], size=n)
    return pd.DataFrame({
        "channel_id": [f"ch_{i:03d}" for i in range(n)],
        "channel_name": [f"channel_{i:03d}" for i in range(n)],
        "theme": themes,
    })


def generate_campaigns(n: int, cfg: dict) -> pd.DataFrame:
    courses = cfg["courses"]
    chosen = [courses[i % len(courses)] for i in range(n)]
    return pd.DataFrame({
        "campaign_id": [f"cmp_{i:03d}" for i in range(n)],
        "campaign_name": chosen,
    })


def generate_creatives(n: int, rng: np.random.Generator) -> pd.DataFrame:
    kinds = rng.choice(["video", "banner", "text"], size=n)
    return pd.DataFrame({
        "creative_id": [f"cr_{i:03d}" for i in range(n)],
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
            "placement_id": f"pl_{i:03d}",
            "campaign_id": cmp_["campaign_id"],
            "channel_id": ch["channel_id"],
            "channel_name": ch["channel_name"],
            "creative_id": cr["creative_id"],
            "cost": float(rng.integers(
                cfg["synthetic"]["cost_min"],
                cfg["synthetic"]["cost_max"],
            )),
            "publication_time": s + pd.Timedelta(seconds=float(rng.uniform(0, span))),
            "data_source": "synthetic",
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Касания вокруг реальных заказов
# --------------------------------------------------------------------------

def generate_touches(
    placements: pd.DataFrame,
    orders: pd.DataFrame,
    cfg: dict,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Для каждого заказа генерируем 1-3 касания в пределах
    attribution window ДО покупки.

    Это ключевое отличие от старой версии: touches привязаны
    к реальным order.student_id и реальным датам покупок.
    """
    window_days = cfg.get("attribution", {}).get("window_days", 7)
    rows = []
    tid = 0

    for _, order in orders.iterrows():
        user_id = order["student_id"]
        order_ts = pd.Timestamp(order["timestamp"])

        # Сколько касаний у этого пользователя до покупки
        n_touches = int(np.clip(rng.poisson(1.5), 1, 3))

        for _ in range(n_touches):
            # Случайный placement
            pl = placements.iloc[int(rng.integers(0, len(placements)))]

            # Касание происходит за [1, window_days] дней до покупки
            days_before = rng.uniform(0.5, window_days)
            ts = order_ts - pd.Timedelta(days=float(days_before))

            # Не раньше начала периода
            s, _ = _dates(cfg)
            if ts < s:
                ts = s + pd.Timedelta(hours=float(rng.uniform(0, 24)))

            # Тип касания
            touch_type = rng.choice(
                ["click", "bot_start", "lead"],
                p=[0.6, 0.3, 0.1],
            )

            sp = (
                f"c_{pl['campaign_id']}"
                f"_p_{pl['placement_id']}"
                f"_cr_{pl['creative_id']}"
            )

            rows.append({
                "touch_id": f"t_{tid:06d}",
                "user_id": int(user_id),          # = student_id из orders
                "touch_type": touch_type,
                "campaign_id": pl["campaign_id"],
                "placement_id": pl["placement_id"],
                "creative_id": pl["creative_id"],
                "timestamp": ts,
                "start_param": sp,
                "data_source": "synthetic",
            })
            tid += 1

    df = pd.DataFrame(rows)
    return df.sort_values(["user_id", "timestamp"]).reset_index(drop=True)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--orders", default="data/orders.csv")
    ap.add_argument("--out-dir", default="data")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    seed = args.seed if args.seed is not None else cfg.get("seed", 42)
    rng = np.random.default_rng(seed)

    # --- читаем реальные заказы ---
    orders_path = Path(args.orders)
    if not orders_path.exists():
        raise FileNotFoundError(
            f"orders.csv not found at {orders_path}. "
            f"Сначала запустите python -m src.normalize_sales"
        )
    orders = pd.read_csv(orders_path, parse_dates=["timestamp"])
    print(f"[synthetic] orders loaded: {len(orders)} rows, "
          f"{orders['student_id'].nunique()} unique students")

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # --- справочники ---
    channels = generate_channels(cfg["synthetic"]["n_channels"], rng)
    campaigns = generate_campaigns(cfg["synthetic"]["n_campaigns"], cfg)
    creatives = generate_creatives(cfg["synthetic"]["n_creatives"], rng)
    placements = generate_placements(
        cfg["synthetic"]["n_placements"],
        channels, campaigns, creatives, cfg, rng,
    )

    # --- касания от реальных заказов ---
    touches = generate_touches(placements, orders, cfg, rng)

    placements.to_csv(out / "ad_registry.csv", index=False)
    touches.to_csv(out / "touches.csv", index=False)

    # --- отчёт ---
    print(f"[synthetic] seed={seed}")
    print(f"[synthetic] placements: {len(placements)} → {out}/ad_registry.csv")
    print(f"[synthetic] touches:    {len(touches)} → {out}/touches.csv")
    print(f"[synthetic] by type:    {touches['touch_type'].value_counts().to_dict()}")
    print(f"[synthetic] unique users in touches: {touches['user_id'].nunique()}")

    # --- проверка связи ---
    order_users = set(orders["student_id"].unique())
    touch_users = set(touches["user_id"].unique())
    matched = len(order_users & touch_users)
    print(f"[synthetic] students with touches: {matched} / {len(order_users)}")
    if matched < len(order_users):
        missing = len(order_users) - matched
        print(f"[synthetic] WARNING: {missing} students have no touches "
              f"(they will be organic in attribution)")


if __name__ == "__main__":
    main()
