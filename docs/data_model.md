# Data Model — Поступашки

Единый контракт sales layer и attribution layer.

## 1. Три уровня знания

### 🟢 Знаем

- 795 строк продаж.
- 628 заказов.
- 606 покупателей.
- 18 курсов.
- Период: 04.08–10.09.2026.
- Один заказ определяется как уникальная пара `(student_id, timestamp)`.
- Несколько курсов с одинаковыми `student_id` и `timestamp` образуют один заказ.
- 153 заказа содержат два и более курса.
- 22 заказа являются повторными относительно доступной истории.
- Общая выручка: 5 904 671,67 ₽.

### 🟡 Оцениваем / моделируем

- attribution: `last_touch`, `linear`, `time_decay`;
- attribution window: 7 дней;
- ROMI по attribution-модели;
- exploratory pre/post analysis вокруг рекламных событий;
- стоимость синтетических размещений.

### 🔴 Нельзя узнать из текущих данных

- реальные marketing costs по каждому placement;
- полный исторический журнал рекламных касаний;
- связь `student_id` с Telegram `user_id` без отдельной mapping-логики;
- истинный incremental effect без эксперимента / holdout.

---

## 2. Canonical sales layer

### `data/order_items.csv`

Одна строка = один курс внутри заказа.

| Колонка | Тип | Описание |
|---|---|---|
| `order_id` | str | детерминированный ID заказа |
| `item_index` | int | позиция курса внутри заказа |
| `student_id` | str | обезличенный ID покупателя |
| `timestamp` | datetime | время покупки |
| `course` | str | курс |
| `amount` | float | сумма строки |

### `data/orders.csv`

Одна строка = один заказ.

| Колонка | Тип | Описание |
|---|---|---|
| `order_id` | str | PK |
| `student_id` | str | покупатель |
| `timestamp` | datetime | время заказа |
| `total_amount` | float | сумма заказа |
| `items_count` | int | число курсов |
| `is_bundle` | bool | `items_count >= 2` |
| `is_repeat` | bool | не первый доступный заказ покупателя |
| `previous_order_id` | str/null | предыдущий заказ |
| `days_since_previous_order` | float/null | дни с предыдущего заказа |

### `data/daily_metrics.csv`

Дневные агрегаты:

`date, orders_count, unique_buyers, revenue, items_count, average_order_value, new_buyers, repeat_orders, bundle_orders`.

---

## 3. Marketing / attribution layer

### `data/ad_registry.csv`

| Колонка | Тип |
|---|---|
| `placement_id` | str |
| `campaign_id` | str |
| `channel_id` | str |
| `channel_name` | str |
| `creative_id` | str |
| `cost` | float |
| `publication_time` | datetime |
| `data_source` | str |

Идентификаторы являются строковыми opaque IDs (`cmp_*`, `pl_*`, `cr_*`, `ch_*`).

### `data/touches.csv`

| Колонка | Тип |
|---|---|
| `touch_id` | str |
| `user_id` | str |
| `touch_type` | click / bot_start / lead |
| `campaign_id` | str |
| `placement_id` | str |
| `creative_id` | str |
| `timestamp` | datetime |
| `start_param` | str |
| `data_source` | str |

### `data/attribution_results.csv`

| Колонка | Тип |
|---|---|
| `order_id` | str |
| `user_id` | str |
| `revenue` | float |
| `campaign_id` | str |
| `placement_id` | str |
| `creative_id` | str |
| `model` | last_touch / linear / time_decay |
| `attributed_revenue` | float |
| `window_days` | int |

---

## 4. Идентификаторы

Не смешиваем:

- `student_id` — обезличенный идентификатор покупателя из sales layer;
- Telegram `user_id` — идентификатор пользователя Telegram;
- `order_id` — детерминированный ID заказа;
- `campaign_id`, `placement_id`, `creative_id`, `channel_id` — строковые marketing IDs.

Связь `student_id ↔ Telegram user_id` не предполагается автоматически. Она появляется только через отдельный stitching / mapping layer.

---

## 5. User stitching

```text
marketing placement
       ↓
tracking link
       ↓
Telegram user_id
       ↓
conversation / lead
       ↓
payment
       ↓
student_id

Если deterministic mapping отсутствует, probabilistic attribution должна быть явно помечена как модельное допущение.

6. ER-диаграмма
7. Правила
Canonical sales source: normalize_sales.py.
Не создаём второй способ формирования order_id.
Не удаляем полные дубли молча.
data_source обязателен для marketing/event data.
Attribution window = 7 дней как рабочее допущение.
Attribution не равна incrementality.
