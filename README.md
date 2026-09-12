# Поступашки — Marketing Measurement System

## MVP

Проект реализует воспроизводимый end-to-end pipeline:

base.xlsx
↓
sales normalization
↓
marketing synthetic layer
↓
identity mapping
↓
multi-touch attribution
↓
attribution reconciliation
↓
ROMI
↓
forecast
↓
business recommendation

## Что реализовано

### 1. Sales layer

- orders
- order_items
- daily_metrics
- EDA
- anomaly detection

Определение заказа:
(student_id, timestamp)

На исходном датасете:

- 795 sales rows
- 628 orders
- 606 buyers
- 18 courses
- 153 bundles
- 22 repeat orders
- 5 904 671.67 ₽ revenue

### 2. Marketing layer

Synthetic marketing data используется только для демонстрации
measurement pipeline, потому что исторические рекламные costs
и полные historical touches отсутствуют.

Generated:

- ad_registry
- touches
- campaigns
- placements
- creatives

### 3. Identity stitching

В production:

Telegram user_id != student_id.

В MVP используется явно маркированный
synthetic_deterministic identity map.

Production solution:
tracking link / Telegram bot / CRM login
→ identity_map
→ student_id

### 4. Attribution

Implemented:

- last touch
- linear
- time decay

Attribution window:
7 days.

Для каждого заказа выполняется revenue reconciliation:

sum(attributed_revenue) == order_amount

### 5. ROMI

ROMI:

(attributed revenue - cost) / cost

Важно:
historical costs отсутствуют, поэтому ROMI на synthetic
marketing layer является демонстрационным.

Это attributed ROMI, а не incremental ROMI.

### 6. Incrementality

Исторический pre/post анализ используется только как exploratory analysis.

Он НЕ интерпретируется как causal estimate.

Для production measurement предлагаем:

- holdout
- DiD
- interrupted time series
- synthetic control

### 7. Forecast

Baseline models:

- 7-day moving average
- weekday mean

Оценка:
rolling-origin backtest.

### 8. Real vs synthetic data

REAL:

- base.xlsx
- normalized sales
- public Telegram posts

SYNTHETIC:

- ad_registry
- touches
- costs
- identity map

Synthetic data нельзя интерпретировать как реальные
исторические рекламные касания или реальные marketing costs.

## Запуск

Установка:

pip install -r requirements.txt

Полный pipeline:

python -m src.pipeline

Тесты:

python -m pytest tests/ -v

Отдельные шаги:

python -m src.normalize_sales
python -m src.build_identity_map
python -m src.generate_synthetic
python -m src.quick_eda
python -m src.attribution
python -m src.romi
python -m src.forecast

## Ограничения

- sales history короткая;
- historical marketing touches неполные;
- historical ad costs отсутствуют;
- Telegram user_id и student_id различаются;
- synthetic layer используется для демонстрации;
- attribution не является incrementality;
- forecast является baseline из-за короткой истории.

## Следующий production step

1. Единый event schema.
2. Tracking links.
3. Telegram bot events.
4. Identity map.
5. CRM/payment events.
6. Реальные advertising costs.
7. Holdout experiment.
8. Incremental ROAS / ROMI.
