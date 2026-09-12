from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")  # без окна, просто сохраняем файлы

# ---------- пути ----------
SRC_DIR = Path(__file__).resolve().parent
ROOT = SRC_DIR.parent
INPUT = ROOT / "base_ready.csv"
FIG_DIR = ROOT / "docs" / "figures"
REP_DIR = ROOT / "reports"
FIG_DIR.mkdir(parents=True, exist_ok=True)
REP_DIR.mkdir(parents=True, exist_ok=True)

print(f"Читаю: {INPUT}")
df = pd.read_csv(INPUT)

# приводим типы
df["Время"] = pd.to_datetime(df["Время"])
df["Дата"] = pd.to_datetime(df["Дата"]).dt.normalize()

print(f"Строк: {len(df)}")
print(f"Колонки: {list(df.columns)}")

# ============================================================
# БЛОК 1. ВЫРУЧКА ПО ДНЯМ
# ============================================================
print("\n=== Блок 1. Выручка по дням ===")

by_day = df.groupby("Дата").agg(
    Выручка=("Сумма", "sum"),
    Строк=("Сумма", "count"),
    Заказов=("Ключ заказа", "nunique"),
    Покупателей=("Номер студента", "nunique"),
).reset_index()

by_day["Средний_чек_строка"] = (by_day["Выручка"] / by_day["Строк"]).round(2)
by_day["Средний_чек_заказ"] = (by_day["Выручка"] / by_day["Заказов"]).round(2)
by_day["Накопительная_выручка"] = by_day["Выручка"].cumsum()
by_day["День_недели"] = by_day["Дата"].dt.day_name()

by_day.to_csv(REP_DIR / "revenue_by_day.csv", index=False, encoding="utf-8-sig")
print(by_day.to_string(index=False))

# график
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(by_day["Дата"], by_day["Выручка"], marker="o", linewidth=2)
ax.set_title("Выручка по дням, 04.08–10.09.2026")
ax.set_xlabel("Дата")
ax.set_ylabel("Выручка, ₽")
ax.grid(alpha=0.3)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(FIG_DIR / "revenue_by_day.png", dpi=150)
plt.close()
print(f"→ {FIG_DIR / 'revenue_by_day.png'}")

# ============================================================
# БЛОК 2. ТОП-КУРСЫ ПО ВЫРУЧКЕ
# ============================================================
print("\n=== Блок 2. Топ-курсы ===")

by_course = df.groupby("Курс").agg(
    Выручка=("Сумма", "sum"),
    Строк=("Сумма", "count"),
    Заказов=("Ключ заказа", "nunique"),
    Покупателей=("Номер студента", "nunique"),
    Средний_чек=("Сумма", "mean"),
).reset_index().sort_values("Выручка", ascending=False)

by_course["Доля_выручки_%"] = (by_course["Выручка"] / by_course["Выручка"].sum() * 100).round(2)
by_course["Накопительная_доля_%"] = by_course["Доля_выручки_%"].cumsum().round(2)

by_course.to_csv(REP_DIR / "top_courses.csv", index=False, encoding="utf-8-sig")
print(by_course.to_string(index=False))

# график топ-10
top10 = by_course.head(10).iloc[::-1]
fig, ax = plt.subplots(figsize=(10, 6))
ax.barh(top10["Курс"], top10["Выручка"], color="#4C72B0")
ax.set_title("Топ-10 курсов по выручке")
ax.set_xlabel("Выручка, ₽")
for i, v in enumerate(top10["Выручка"]):
    ax.text(v, i, f" {v:,.0f}", va="center", fontsize=9)
plt.tight_layout()
plt.savefig(FIG_DIR / "top_courses.png", dpi=150)
plt.close()
print(f"→ {FIG_DIR / 'top_courses.png'}")

# ============================================================
# БЛОК 3. ПОВТОРНЫЕ ПОКУПКИ
# ============================================================
print("\n=== Блок 3. Повторные покупки ===")

orders_per_student = df.groupby("Номер студента")["Ключ заказа"].nunique().reset_index()
orders_per_student.columns = ["Номер студента", "Кол-во заказов"]

orders_per_student.to_csv(REP_DIR / "orders_per_student.csv", index=False, encoding="utf-8-sig")

dist = orders_per_student["Кол-во заказов"].value_counts().sort_index().reset_index()
dist.columns = ["Кол-во заказов", "Кол-во студентов"]
dist["Доля_%"] = (dist["Кол-во студентов"] / dist["Кол-во студентов"].sum() * 100).round(2)

dist.to_csv(REP_DIR / "repeat_purchases.csv", index=False, encoding="utf-8-sig")
print(dist.to_string(index=False))

total_buyers = dist["Кол-во студентов"].sum()
repeat_buyers = dist[dist["Кол-во заказов"] > 1]["Кол-во студентов"].sum()
print(f"\nВсего покупателей: {total_buyers}")
print(f"Повторных: {repeat_buyers} ({repeat_buyers/total_buyers*100:.1f}%)")
print(f"Среднее заказов на покупателя: {orders_per_student['Кол-во заказов'].mean():.2f}")

# график
fig, ax = plt.subplots(figsize=(8, 5))
ax.bar(dist["Кол-во заказов"].astype(str), dist["Кол-во студентов"], color="#55A868")
ax.set_title("Распределение покупателей по числу заказов")
ax.set_xlabel("Кол-во заказов")
ax.set_ylabel("Кол-во студентов")
for i, v in enumerate(dist["Кол-во студентов"]):
    ax.text(i, v, str(v), ha="center", va="bottom")
plt.tight_layout()
plt.savefig(FIG_DIR / "repeat_purchases.png", dpi=150)
plt.close()
print(f"→ {FIG_DIR / 'repeat_purchases.png'}")

# ============================================================
# БЛОК 4. РАСПРЕДЕЛЕНИЕ ЧЕКОВ
# ============================================================
print("\n=== Блок 4. Распределение чеков ===")

# базовая статистика
stats = {
    "Строк": len(df),
    "Уникальных покупателей": df["Номер студента"].nunique(),
    "Уникальных заказов": df["Ключ заказа"].nunique(),
    "Уникальных курсов": df["Курс"].nunique(),
    "Общая выручка": df["Сумма"].sum(),
    "Средний чек (строка)": df["Сумма"].mean(),
    "Медиана чека": df["Сумма"].median(),
    "Мин. чек": df["Сумма"].min(),
    "Макс. чек": df["Сумма"].max(),
    "25-й перцентиль": df["Сумма"].quantile(0.25),
    "75-й перцентиль": df["Сумма"].quantile(0.75),
    "Стд. отклонение": df["Сумма"].std(),
    "Период с": df["Дата"].min().date(),
    "Период по": df["Дата"].max().date(),
    "Дней с продажами": df["Дата"].nunique(),
    "Средняя выручка в день": df["Сумма"].sum() / df["Дата"].nunique(),
}

stats_df = pd.DataFrame(list(stats.items()), columns=["Метрика", "Значение"])
stats_df.to_csv(REP_DIR / "summary_stats.csv", index=False, encoding="utf-8-sig")
print(stats_df.to_string(index=False))

# топ-10 частых сумм
top_amounts = df["Сумма"].value_counts().head(10).reset_index()
top_amounts.columns = ["Сумма", "Кол-во"]
top_amounts.to_csv(REP_DIR / "top_amounts.csv", index=False, encoding="utf-8-sig")
print("\nТоп-10 самых частых сумм:")
print(top_amounts.to_string(index=False))

# корзины
bins = [0, 1000, 3000, 5000, 7000, 9000, 12000, float("inf")]
labels = ["<1000", "1000-3000", "3000-5000", "5000-7000", "7000-9000", "9000-12000", "12000+"]
df["Корзина"] = pd.cut(df["Сумма"], bins=bins, labels=labels, right=False)

buckets = df["Корзина"].value_counts().reindex(labels).reset_index()
buckets.columns = ["Корзина", "Кол-во"]
buckets["Доля_%"] = (buckets["Кол-во"] / buckets["Кол-во"].sum() * 100).round(2)
buckets.to_csv(REP_DIR / "check_distribution.csv", index=False, encoding="utf-8-sig")
print("\nРаспределение чеков по корзинам:")
print(buckets.to_string(index=False))

# график
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(buckets["Корзина"], buckets["Кол-во"], color="#C44E52")
ax.set_title("Распределение чеков по корзинам")
ax.set_xlabel("Сумма, ₽")
ax.set_ylabel("Кол-во строк")
for i, v in enumerate(buckets["Кол-во"]):
    ax.text(i, v, str(v), ha="center", va="bottom")
plt.tight_layout()
plt.savefig(FIG_DIR / "check_distribution.png", dpi=150)
plt.close()
print(f"→ {FIG_DIR / 'check_distribution.png'}")

# ============================================================
# БЛОК 5. АНОМАЛИИ (бонус)
# ============================================================
print("\n=== Блок 5. Аномалии ===")

low = df[df["Сумма"] < 3000].sort_values("Сумма")
low.to_csv(REP_DIR / "anomaly_low_amounts.csv", index=False, encoding="utf-8-sig")
print(f"Подозрительно низких сумм (<3000): {len(low)}")

high = df[df["Сумма"] > 15000].sort_values("Сумма", ascending=False)
high.to_csv(REP_DIR / "anomaly_high_amounts.csv", index=False, encoding="utf-8-sig")
print(f"Подозрительно высоких сумм (>15000): {len(high)}")

simultaneous = df.groupby(["Номер студента", "Время"]).size().reset_index(name="Кол-во")
simultaneous = simultaneous[simultaneous["Кол-во"] > 1].sort_values("Кол-во", ascending=False)
simultaneous.to_csv(REP_DIR / "anomaly_simultaneous.csv", index=False, encoding="utf-8-sig")
print(f"Одновременных покупок (пакетов): {len(simultaneous)}")

print("\n=== ГОТОВО ===")
print(f"CSV с отчётами: {REP_DIR}")
print(f"Графики: {FIG_DIR}")