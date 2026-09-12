import pandas as pd
from pathlib import Path

DATA = Path("data")

df = pd.read_csv(DATA / "posts_postypashki_old.csv")

print("Всего строк:", len(df))
print("Уникальных post_id:", df["post_id"].nunique())
print("Мин. дата:", df["date"].min())
print("Макс. дата:", df["date"].max())
print("Дубли по post_id:", df["post_id"].duplicated().sum())

df["date"] = pd.to_datetime(df["date"])
daily = df.groupby("date").size().sort_values(ascending=False)
print("\nТоп-10 дней по числу постов:")
print(daily.head(10))