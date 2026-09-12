import pandas as pd

# Продажи
sales = pd.read_excel("data/base.xlsx")
sales.columns = ["student_id", "amount", "course", "timestamp"]
sales["date"] = pd.to_datetime(sales["timestamp"]).dt.date

sales_daily = sales.groupby("date").agg(
    revenue=("amount", "sum"),
    orders=("student_id", "nunique"),
).reset_index()

# Посты
posts = pd.read_csv("data/posts_postypashki_old.csv")
posts["date"] = pd.to_datetime(posts["date"]).dt.date

posts_daily = posts.groupby("date").agg(
    posts=("post_id", "count"),
).reset_index()

# Связка
merged = sales_daily.merge(posts_daily, on="date", how="outer").fillna(0)
merged = merged.sort_values("date")
merged.to_csv("sales_posts_daily.csv", index=False)

print(merged.to_string())