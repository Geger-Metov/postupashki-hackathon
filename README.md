# Поступашки — marketing attribution hackathon

Проект для анализа продаж и построения measurement / attribution системы для маркетинговых активностей.

Текущий статус

Репозиторий находится на этапе Stage 1.5 — стабилизация data contract.

Canonical sales pipeline уже нормализован:

data/base.xlsx
      ↓
src/normalize_sales.py
      ↓
┌───────────────────────┐
│ orders.csv            │
│ order_items.csv       │
│ daily_metrics.csv     │
└───────────────────────┘

На текущем наборе данных:

Метрика Значение
Строк продаж 795
Заказов 628
Покупателей 606
Курсов 18
Пакетных заказов 153
Повторных заказов 22
Выручка 5 904 671,67 ₽

Пакет и повторная покупка являются операционными определениями, а не утверждениями о бизнес-процессах, которых нет в исходном файле.

Архитектура
Sales layer
base.xlsx
   ↓
normalize_sales.py
   ├── order_items.csv
   ├── orders.csv
   └── daily_metrics.csv
Marketing layer
ad_registry.csv
      ↓
touches.csv
      ↓
user stitching
      ↓
attribution
      ↓
ROMI
Attribution ≠ incrementality

Attribution отвечает, как распределить уже случившуюся выручку между касаниями.

Incrementality отвечает, какую дополнительную выручку действительно создала реклама.

Эти задачи разделены в архитектуре проекта.

Запуск
Нормализация продаж
python -m src.normalize_sales
EDA
python -m src.quick_eda
Синтетический marketing layer
python -m src.generate_synthetic
Связка продаж и постов
python -m src.join_sales_posts
Exploratory pre/post analysis
python -m src.incrementality --date 2026-08-08
Тесты
python -m pytest tests/ -v
Stage 1.5 pipeline
python -m src.pipeline

Pipeline намеренно не объявляет attribution / ROMI готовыми шагами, пока соответствующие production-модули не реализованы.

Структура
data/
  base.xlsx
  orders.csv
  order_items.csv
  daily_metrics.csv
  ad_registry.csv
  touches.csv
  posts_*.csv

docs/
  definitions.md
  assumptions.md
  anomalies.md
  data_model.md
  causal_design.md
  executive_summary.md
  executive_summary_from_rashid.md

src/
  normalize_sales.py
  quick_eda.py
  join_sales_posts.py
  generate_synthetic.py
  tracking_bot.py
  incrementality.py
  pipeline.py
  ...

tests/
  test_sales_normalization.py
  test_synthetic.py
  test_stage_1_5.py
Важные ограничения
История продаж начинается 04.08.2026.
Исторические рекламные касания неполны.
Реальные costs размещений отсутствуют.
student_id и Telegram user_id — разные идентификаторы.
Synthetic touches не следует интерпретировать как реальные исторические касания покупателей.
Pre/post анализ не доказывает причинность.
Следующий этап

После стабилизации Stage 1.5:

реализовать attribution engine;
задать единый контракт touches → order;
добавить synthetic end-to-end тестовый контур;
проверить last-touch / linear / time-decay;
затем считать ROMI;
отдельно развивать incrementality / experimental design.
