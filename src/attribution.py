"""
Multi-touch attribution engine.

Вход:
    data/touches.csv        (или data/processed/touches.csv)
        touch_id, user_id, campaign_id, placement_id, creative_id,
        source_type (или touch_type), timestamp, data_source
    data/orders.csv         (или data/processed/orders.csv)
        order_id, student_id (или user_id), total_amount, timestamp

Выход:
    data/attribution_results.csv

Модели:
    last_touch   — 100% веса последнему касанию в окне
    linear       — равные доли всем касаниям в окне
    time_decay   — экспоненциальное затухание с half-life

Attribution window:
    WINDOW_DAYS дней до покупки (по умолчанию 7).

ASSUMPTION (критично):
    touches.user_id и orders.student_id живут в одном пространстве ID.
    В этом репозитории student_id из orders используется как user_id
    в touches — это MOCK-stitching для демонстрации механики.
    Реального identity resolution между Telegram и sales layer нет,
    и это должно быть явно написано в README.
"""
from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

log = logging.getLogger("attribution")

DEFAULT_DATA_DIR = Path("data")
ALT_DATA_DIR = Path("data/processed")

# Порядок важен: сначала user_id, потом student_id.
USER_COL_CANDIDATES = ("user_id", "student_id")
TOUCH_TYPE_CANDIDATES = ("source_type", "touch_type")


# --------------------------------------------------------------------------
# Конфиг
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class AttributionConfig:
    window_days: int = 7
    half_life_days: float = 3.0
    models: tuple[str, ...] = ("last_touch", "linear", "time_decay")
    strict: bool = False
    organic_warn_share: float = 0.5


# --------------------------------------------------------------------------
# Веса
# --------------------------------------------------------------------------

def _weights_last_touch(
    touches: pd.DataFrame, order_ts: pd.Timestamp, cfg: AttributionConfig
) -> np.ndarray:
    w = np.zeros(len(touches))
    w[-1] = 1.0
    return w


def _weights_linear(
    touches: pd.DataFrame, order_ts: pd.Timestamp, cfg: AttributionConfig
) -> np.ndarray:
    n = len(touches)
    return np.full(n, 1.0 / n)


def _weights_time_decay(
    touches: pd.DataFrame, order_ts: pd.Timestamp, cfg: AttributionConfig
) -> np.ndarray:
    ages = (order_ts - touches["timestamp"]).dt.total_seconds() / 86400.0
    ages = ages.clip(lower=0.0)  # защита от касаний "в будущем"
    raw = 0.5 ** (ages / cfg.half_life_days)
    total = float(raw.sum())
    if total <= 0 or not np.isfinite(total):
        return np.full(len(touches), 1.0 / len(touches))
    return (raw / total).to_numpy()


WEIGHT_FUNCS: dict[str, Callable[..., np.ndarray]] = {
    "last_touch": _weights_last_touch,
    "linear": _weights_linear,
    "time_decay": _weights_time_decay,
}


# --------------------------------------------------------------------------
# Утилиты разрешения колонок
# --------------------------------------------------------------------------

def _resolve_col(
    df: pd.DataFrame,
    requested: str,
    candidates: tuple[str, ...],
) -> str:
    """
    requested="auto" — ищем первую существующую из candidates.
    Иначе — проверяем, что requested есть в df.
    """
    if requested != "auto":
        if requested not in df.columns:
            raise ValueError(
                f"column '{requested}' not found in columns: {list(df.columns)}"
            )
        return requested
    for c in candidates:
        if c in df.columns:
            return c
    raise ValueError(
        f"none of {candidates} found in columns: {list(df.columns)}"
    )


def _resolve_data_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        if not explicit.exists():
            raise FileNotFoundError(f"data dir not found: {explicit}")
        return explicit
    # предпочитаем data/, но если там файлов нет — data/processed/
    for d in (DEFAULT_DATA_DIR, ALT_DATA_DIR):
        if (d / "orders.csv").exists() and (d / "touches.csv").exists():
            return d
    # если ничего не нашли — вернём data/, пусть упадёт на чтении
    return DEFAULT_DATA_DIR


# --------------------------------------------------------------------------
# Подготовка
# --------------------------------------------------------------------------

def _prepare_touches(
    df: pd.DataFrame,
    user_col_requested: str = "auto",
    type_col_requested: str = "auto",
) -> pd.DataFrame:
    df = df.copy()

    user_col = _resolve_col(df, user_col_requested, USER_COL_CANDIDATES)
    if user_col != "user_id":
        df = df.rename(columns={user_col: "user_id"})

    type_col = _resolve_col(df, type_col_requested, TOUCH_TYPE_CANDIDATES)
    if type_col != "source_type":
        df = df.rename(columns={type_col: "source_type"})

    required = {"user_id", "timestamp"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"touches missing columns: {sorted(missing)}")

    # timestamp -> datetime, NaN -> drop с предупреждением
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    bad_ts = df["timestamp"].isna()
    if bad_ts.any():
        log.warning("touches: dropping %d rows with invalid timestamp", int(bad_ts.sum()))
        df = df.loc[~bad_ts]

    # user_id NaN -> drop
    bad_uid = df["user_id"].isna()
    if bad_uid.any():
        log.warning("touches: dropping %d rows with NaN user_id", int(bad_uid.sum()))
        df = df.loc[~bad_uid]

    # гарантируем наличие опциональных колонок
    for col in ("touch_id", "campaign_id", "placement_id",
                "creative_id", "data_source"):
        if col not in df.columns:
            df[col] = None

    df = df.sort_values(["user_id", "timestamp"]).reset_index(drop=True)
    return df


def _prepare_orders(
    df: pd.DataFrame,
    user_col_requested: str = "auto",
) -> pd.DataFrame:
    df = df.copy()

    user_col = _resolve_col(df, user_col_requested, USER_COL_CANDIDATES)
    if user_col != "user_id":
        df = df.rename(columns={user_col: "user_id"})

    required = {"order_id", "user_id", "total_amount", "timestamp"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"orders missing columns: {sorted(missing)}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    bad_ts = df["timestamp"].isna()
    if bad_ts.any():
        log.warning("orders: dropping %d rows with invalid timestamp", int(bad_ts.sum()))
        df = df.loc[~bad_ts]

    df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce")
    df = df.dropna(subset=["user_id", "total_amount", "order_id"])

    return df.reset_index(drop=True)


# --------------------------------------------------------------------------
# Атрибуция
# --------------------------------------------------------------------------

def _organic_rows(order: pd.Series, models: tuple[str, ...]) -> list[dict]:
    out = []

    for model in models:
        out.append({
            "order_id": order["order_id"],
            "user_id": order["user_id"],
            "order_timestamp": order["timestamp"],
            "order_amount": float(order["total_amount"]),
            "model": model,
            "touch_id": None,
            "campaign_id": None,
            "placement_id": None,
            "creative_id": None,
            "source_type": "organic",
            "touch_timestamp": pd.NaT,
            "window_days": None,
            "weight": 1.0,
            "attributed_revenue": float(order["total_amount"]),
        })

    return out


def _attribute_one_order(
    order: pd.Series,
    touches_by_user: dict,
    cfg: AttributionConfig,
) -> list[dict]:
    user_id = order["user_id"]
    order_ts = order["timestamp"]
    window_start = order_ts - pd.Timedelta(days=cfg.window_days)

    user_touches = touches_by_user.get(user_id)
    if user_touches is None or user_touches.empty:
        return _organic_rows(order, cfg.models)

    relevant = user_touches[
        (user_touches["timestamp"] >= window_start)
        & (user_touches["timestamp"] <= order_ts)
    ]

    if relevant.empty:
        return _organic_rows(order, cfg.models)

    rows: list[dict] = []
    for model in cfg.models:
        weights = WEIGHT_FUNCS[model](relevant, order_ts, cfg)
        for (_, t), w in zip(relevant.iterrows(), weights):
            rows.append({
                "order_id": order["order_id"],
                "user_id": user_id,
                "order_timestamp": order_ts,
                "order_amount": float(order["total_amount"]),
                "model": model,
                "touch_id": t["touch_id"],
                "campaign_id": t.get("campaign_id"),
                "placement_id": t["placement_id"],
                "creative_id": t["creative_id"],
                "source_type": t["source_type"],
                "touch_timestamp": t["timestamp"],
                "window_days": cfg.window_days,
                "weight": float(w),
                "attributed_revenue": float(order["total_amount"]) * float(w),
            })
            
    return rows


def run_attribution(
    touches: pd.DataFrame,
    orders: pd.DataFrame,
    cfg: AttributionConfig,
    touches_user_col: str = "auto",
    orders_user_col: str = "auto",
    touches_type_col: str = "auto",
) -> pd.DataFrame:
    touches = _prepare_touches(touches, touches_user_col, touches_type_col)
    orders = _prepare_orders(orders, orders_user_col)

    log.info("touches: %d rows, %d unique users",
             len(touches), touches["user_id"].nunique())
    log.info("orders:  %d rows, %d unique users",
             len(orders), orders["user_id"].nunique())

    touches_by_user = {uid: g for uid, g in touches.groupby("user_id")}

    matched = len(set(orders["user_id"]) & set(touches_by_user))
    total_users = orders["user_id"].nunique()
    log.info("users with at least one touch: %d / %d", matched, total_users)

    all_rows: list[dict] = []
    for _, order in orders.iterrows():
        all_rows.extend(_attribute_one_order(order, touches_by_user, cfg))

    results = pd.DataFrame(all_rows)
    results = results.sort_values(
        ["model", "order_id", "touch_timestamp"]
    ).reset_index(drop=True)
    return results


# --------------------------------------------------------------------------
# Отчёты
# --------------------------------------------------------------------------

def summary_by_model(results: pd.DataFrame) -> pd.DataFrame:
    return (
        results.groupby("model")
        .agg(
            attributed_revenue=("attributed_revenue", "sum"),
            orders=("order_id", "nunique"),
            touches=("touch_id", "nunique"),
        )
        .reset_index()
    )


def summary_by_placement(results: pd.DataFrame) -> pd.DataFrame:
    df = results[results["placement_id"].notna()].copy()
    if df.empty:
        return df
    return (
        df.groupby(["model", "placement_id"])
        .agg(
            attributed_revenue=("attributed_revenue", "sum"),
            orders=("order_id", "nunique"),
            touches=("touch_id", "nunique"),
        )
        .reset_index()
        .sort_values(["model", "attributed_revenue"], ascending=[True, False])
    )


def organic_share(results: pd.DataFrame) -> pd.Series:
    """Доля органики по каждой модели."""
    return (
        results.assign(is_organic=results["source_type"] == "organic")
        .groupby("model")["is_organic"]
        .mean()
    )


def reconciliation(results: pd.DataFrame) -> pd.DataFrame:
    """
    Проверка сохранения выручки.

    Для каждого order_id и attribution model:
        sum(attributed_revenue) == order_amount

    Проверяются и paid touches, и organic orders.
    """
    grp = (
        results
        .groupby(["model", "order_id"], as_index=False)
        .agg(
            attributed=("attributed_revenue", "sum"),
            amount=("order_amount", "first"),
        )
    )

    grp["diff"] = (grp["attributed"] - grp["amount"]).abs()

    return grp


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Multi-touch attribution")
    p.add_argument("--data-dir", type=Path, default=None,
                   help="Каталог с touches.csv и orders.csv "
                        "(по умолчанию auto-detect: data/ или data/processed/)")
    p.add_argument("--touches", type=Path, default=None)
    p.add_argument("--orders", type=Path, default=None)
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--window-days", type=int, default=7,
                   help="Attribution window в днях до покупки")
    p.add_argument("--half-life-days", type=float, default=3.0,
                   help="Half-life для time_decay в днях")
    p.add_argument("--touches-user-col", type=str, default="auto")
    p.add_argument("--orders-user-col", type=str, default="auto")
    p.add_argument("--touches-type-col", type=str, default="auto")
    p.add_argument("--strict", action="store_true",
                   help="Падать, если reconciliation не сходится")
    return p


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _build_argparser().parse_args(argv)

    data_dir = _resolve_data_dir(args.data_dir)
    touches_path = args.touches or (data_dir / "touches.csv")
    orders_path = args.orders or (data_dir / "orders.csv")
    output_path = args.output or (data_dir / "attribution_results.csv")

    log.info("data_dir: %s", data_dir)
    log.info("touches:  %s", touches_path)
    log.info("orders:   %s", orders_path)

    touches = pd.read_csv(touches_path)
    orders = pd.read_csv(orders_path)

    cfg = AttributionConfig(
        window_days=args.window_days,
        half_life_days=args.half_life_days,
        strict=args.strict,
    )
    log.info("config: window=%sd, half_life=%sd, models=%s",
             cfg.window_days, cfg.half_life_days, cfg.models)

    results = run_attribution(
        touches, orders, cfg,
        touches_user_col=args.touches_user_col,
        orders_user_col=args.orders_user_col,
        touches_type_col=args.touches_type_col,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_path, index=False)

    # --- organic share ---
    org = organic_share(results)
    log.info("\nOrganic share by model:\n%s", org.to_string())
    if (org > cfg.organic_warn_share).any():
        log.warning(
            "ВЫСОКАЯ ДОЛЯ ОРГАНИКИ (>%.0f%%). Скорее всего user_id "
            "в touches и student_id в orders из разных пространств ID. "
            "Проверьте generate_synthetic.py.",
            cfg.organic_warn_share * 100,
        )

    # --- reconciliation ---
    recon = reconciliation(results)
    if not recon.empty:
        max_diff = float(recon["diff"].max())

    log.info(
        "reconciliation: max |attributed - amount| = %.6f",
        max_diff,
    )

    if max_diff > 1e-6:
        msg = "Модели распределяют не всю сумму заказа"
        if cfg.strict:
            raise AssertionError(msg)
        log.warning(msg)

    log.info("\nBy model:\n%s", summary_by_model(results).to_string(index=False))

    top = summary_by_placement(results).query("model == 'last_touch'").head(10)
    if not top.empty:
        log.info("\nTop placements (last_touch):\n%s", top.to_string(index=False))

    log.info("\nWrote %d rows to %s", len(results), output_path)


if __name__ == "__main__":
    main()
