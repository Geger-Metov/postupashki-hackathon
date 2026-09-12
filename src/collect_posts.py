import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import time

CHANNEL = "postypashki_old"
DATE_FROM = datetime(2026, 7, 28)
DATE_TO   = datetime(2026, 9, 10, 23, 59)
OUTPUT = "posts_postypashki_old.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def fetch_channel(username, date_from, date_to, max_pages=200):
    posts = []
    before = None
    session = requests.Session()
    session.headers.update(HEADERS)

    for page in range(max_pages):
        url = f"https://t.me/s/{username}"
        if before:
            url += f"?before={before}"
        try:
            r = session.get(url, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print(f"Ошибка запроса: {e}")
            break

        soup = BeautifulSoup(r.text, "lxml")
        blocks = soup.select("div.tgme_widget_message_wrap")

        if not blocks:
            print(f"Стр. {page+1}: посты не найдены")
            break

        oldest_dt = None
        for block in blocks:
            text_el = block.select_one("div.tgme_widget_message_text")
            text = text_el.get_text("\n", strip=True) if text_el else ""

            time_el = block.select_one("time")
            if not time_el or not time_el.get("datetime"):
                continue
            dt = datetime.fromisoformat(
                time_el["datetime"].replace("Z", "+00:00")
            ).replace(tzinfo=None)

            post_id = None
            msg = block.select_one("div.tgme_widget_message[data-post]")
            if msg:
                post_id = msg["data-post"].split("/")[-1]

            if oldest_dt is None or dt < oldest_dt:
                oldest_dt = dt

            if dt < date_from or dt > date_to:
                continue

            posts.append({
                "date": dt.date().isoformat(),
                "time": dt.strftime("%H:%M:%S"),
                "datetime": dt.isoformat(),
                "channel": username,
                "post_id": post_id,
                "text": text,
                "link": f"https://t.me/{username}/{post_id}" if post_id else "",
            })

        print(f"Стр. {page+1}: всего {len(posts)} постов, oldest={oldest_dt}")

        if oldest_dt is None or oldest_dt < date_from:
            break

        first_msg = blocks[0].select_one("div.tgme_widget_message[data-post]")
        if first_msg:
            before = first_msg["data-post"].split("/")[-1]
        else:
            break
        time.sleep(1.5)

    return posts


if __name__ == "__main__":
    print(f"=== Сбор канала: {CHANNEL} ===")
    posts = fetch_channel(CHANNEL, DATE_FROM, DATE_TO)
    if not posts:
        print("Ничего не собрано. Проверь, публичный ли канал.")
    else:
        df = pd.DataFrame(posts).sort_values("datetime").reset_index(drop=True)
        df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
        print(f"\n✅ Сохранено {len(df)} постов в {OUTPUT}")
        print(df[["date", "time"]].head(10))