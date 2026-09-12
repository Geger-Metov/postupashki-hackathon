"""
Простой воспроизводимый forecast daily revenue.

Модели:
1. mean_7d      — среднее последних 7 дней
2. weekday_mean — среднее по соответствующему дню недели

Оценка:
rolling-origin backtest.

Мы намеренно не используем сложный ML:
история короткая, поэтому baseline является более честным.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DATA = Path("data")


def load_daily_revenue(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    if "date" not in df.columns:
        raise ValueError("daily_metrics.csv должен содержать date")

    df["date"] = pd.to_datetime(df["date"])
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")

    df = (
        df[["date", "revenue"]]
        .dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )

    return df


def mean_7d_forecast(train: pd.DataFrame) -> float:
    return float(train["revenue"].tail(7).mean())


def weekday_mean_forecast(
    train: pd.DataFrame,
    target_date: pd.Timestamp,
) -> float:
    weekday = target_date.dayofweek

    same_weekday = train[
        train["date"].dt.dayofweek == weekday
    ]

    if same_weekday.empty:
        return mean_7d_forecast(train)

    return float(same_weekday["revenue"].mean())


def mae(y_true, y_pred) -> float:
    return float(np.mean(np.abs(np.asarray(y_true) - np.asarray(y_pred))))


def mape(y_true, y_pred) -> float:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    mask = y_true != 0

    if not mask.any():
        return np.nan

    return float(
        np.mean(
            np.abs(
                (y_true[mask] - y_pred[mask])
                / y_true[mask]
            )
        ) * 100
    )


def backtest(
    daily: pd.DataFrame,
    min_train_days: int = 14,
) -> pd.DataFrame:

    rows = []

    for i in range(min_train_days, len(daily)):
        train = daily.iloc[:i]
        test = daily.iloc[i]

        target_date = test["date"]
        actual = float(test["revenue"])

        pred_7d = mean_7d_forecast(train)
        pred_weekday = weekday_mean_forecast(train, target_date)

        rows.append({
            "date": target_date,
            "actual": actual,
            "mean_7d": pred_7d,
            "weekday_mean": pred_weekday,
        })

    return pd.DataFrame(rows)


def forecast_next(
    daily: pd.DataFrame,
    horizon: int = 7,
) -> pd.DataFrame:

    train = daily.copy()
    last_date = train["date"].max()

    rows = []

    for step in range(1, horizon + 1):
        date = last_date + pd.Timedelta(days=step)

        pred_7d = mean_7d_forecast(train)
        pred_weekday = weekday_mean_forecast(train, date)

        rows.append({
            "date": date,
            "mean_7d": pred_7d,
            "weekday_mean": pred_weekday,
        })

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--daily",
        default="data/daily_metrics.csv",
    )

    parser.add_argument(
        "--horizon",
        type=int,
        default=7,
    )

    args = parser.parse_args()

    daily = load_daily_revenue(Path(args.daily))

    bt = backtest(daily)

    metrics = pd.DataFrame([
        {
            "model": "mean_7d",
            "MAE": mae(bt["actual"], bt["mean_7d"]),
            "MAPE_pct": mape(bt["actual"], bt["mean_7d"]),
        },
        {
            "model": "weekday_mean",
            "MAE": mae(bt["actual"], bt["weekday_mean"]),
            "MAPE_pct": mape(bt["actual"], bt["weekday_mean"]),
        },
    ])

    predictions = forecast_next(
        daily,
        horizon=args.horizon,
    )

    DATA.mkdir(exist_ok=True)

    bt.to_csv(
        DATA / "forecast_backtest.csv",
        index=False,
    )

    metrics.to_csv(
        DATA / "forecast_metrics.csv",
        index=False,
    )

    predictions.to_csv(
        DATA / "forecast_next.csv",
        index=False,
    )

    print("\nForecast backtest:")
    print(metrics.to_string(index=False))

    print("\nNext forecast:")
    print(predictions.to_string(index=False))


if __name__ == "__main__":
    main()