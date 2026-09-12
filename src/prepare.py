import pandas as pd

# читаем исходник
df = pd.read_excel("/Users/jaehaerz/Desktop/postupashki/src/base.xlsx", sheet_name="Данные")

# колонка "Дата" — только день
df["Дата"] = pd.to_datetime(df["Время"]).dt.normalize()

# колонка "Ключ заказа" = student_id + timestamp
df["Ключ заказа"] = df["Номер студента"].astype(str) + "|" + df["Время"].astype(str)

# сохраняем готовый CSV
df.to_csv("base_ready.csv", index=False, encoding="utf-8-sig")

print(f"Готово! Строк: {len(df)}")
print(df.head())