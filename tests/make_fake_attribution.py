"""Временный генератор фейкового attribution_results.csv.

Нужен ТОЛЬКО для проверки romi.py до прихода реального файла от Разраба №1.
Не коммитить в прод.
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(0)
touches = pd.read_csv("data/touches.csv")
leads = touches[touches.touch_type == "lead"]

rows = []
for i, t in leads.iterrows():
    for model in ["last_touch", "linear", "time_decay"]:
        rows.append({
            "order_id": f"o_{i:06d}",
            "user_id": t.user_id,
            "revenue": float(rng.integers(1000, 20000)),
            "campaign_id": t.campaign_id,
            "placement_id": t.placement_id,
            "creative_id": t.creative_id,
            "model": model,
            "attributed_revenue": float(rng.integers(500, 15000)),
            "window_days": 7,
        })
pd.DataFrame(rows).to_csv("data/attribution_results.csv", index=False)
print(f"[fake] written {len(rows)} rows → data/attribution_results.csv")