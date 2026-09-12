# Executive Summary — Поступашки

Проблема

Telegram — важный канал продаж, но исторические маркетинговые касания не логируются полностью. В base.xlsx видим 795 строк продаж, которые после нормализации образуют 628 заказов и 606 покупателей за период 04.08–10.09.2026.

Бизнес-вопрос: какие рекламные активности приносят деньги и куда направить следующие 300 000 ₽?

Данные
Реальные: base.xlsx — 795 строк, 628 заказов, 606 покупателей, 18 курсов.
Нормализованные: orders.csv, order_items.csv, daily_metrics.csv.
Синтетические: registry размещений и касания для прототипирования attribution.
Собранные: публичные Telegram-посты, где они доступны.
Основные выводы
🟢 Знаем
Один заказ = (student_id, timestamp).
Пакет = заказ с items_count >= 2.
В нормализованных данных: 153 пакетных заказа.
Повторный заказ = не первый доступный заказ пользователя; таких 22.
История начинается 04.08.2026, поэтому историческую повторность до начала периода установить нельзя.
Общая выручка: 5 904 671,67 ₽.
🟡 Оцениваем
ROMI_attr = (Attributed Revenue − Cost) / Cost по attribution-модели.
Attribution: last_touch, linear, time_decay, окно 7 дней.
Pre/post анализ вокруг рекламных событий используется как exploratory analysis.
🔴 Нельзя узнать
реальные costs по историческим размещениям;
полные исторические касания;
deterministic связь student_id ↔ Telegram user_id без отдельного mapping;
incremental effect без эксперимента / holdout.
Архитектура
sales
  ↓
normalize_sales
  ↓
orders / order_items / daily_metrics

marketing
  ↓
ad_registry / touches
  ↓
stitching
  ↓
attribution
  ↓
ROMI

Ключевой принцип:

attribution показывает, какой канал модель связывает с уже случившейся выручкой; incrementality отвечает на вопрос, добавила ли реклама эту выручку.

Что делать с бюджетом 300 000 ₽
Внедрить tracking links для внешних размещений.
Логировать publication_time и cost каждого placement.
Связывать start_param → Telegram user_id → lead → payment.
Использовать ROMI_attr для первичной приоритизации.
Для финального решения использовать экспериментальный incremental effect.
Не выдавать synthetic ROMI за исторический факт.
Ограничения
короткая история наблюдения;
отсутствуют реальные исторические marketing costs;
исторические касания неполны;
synthetic layer не связан автоматически с реальными student_id;
текущий incrementality модуль — descriptive pre/post analysis, а не полноценная causal ITS.
