import pandas as pd

posts = pd.read_csv("data/posts_postypashki_old.csv")

def classify(text):
    t = str(text).lower()
    if any(w in t for w in ["скидка", "промокод", "акция", "только сегодня"]):
        return "discount"
    if any(w in t for w in ["старт", "набор", "запуск", "открыт", "залетай"]):
        return "launch"
    if any(w in t for w in ["курс", "обучение", "менеджер", "записаться", "напиши"]):
        return "sale"
    return "content"

posts["post_type"] = posts["text"].apply(classify)
posts.to_csv("data/posts_classified.csv", index=False, encoding="utf-8-sig")

print(posts["post_type"].value_counts())
