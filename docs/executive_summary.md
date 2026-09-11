# Executive summary

## Проблема
Воронка Поступашек — black box.
Видим оплату и курс, но не видим рекламу, касания и лиды.
ROMI посчитать нельзя.

## Данные
base.xlsx: 795 строк, 606 покупателей, 18 продуктов, 04.08–10.09.2026.

## Что знаем
- Заказы, выручка, повторные покупки.
- Пакеты (несколько курсов в один заказ).
- Аномалии сумм: 500, 1000, 18900, 19350.
- Всплески по датам, совпадающие с постами.

## Чего не хватает
- Касания: клики, переходы, лиды.
- Cost размещений.
- Placement, creative, campaign.
- Incremental-эффект.

## Решение
MVP: base.xlsx → orders → posts → classification → match → touches → attribution → ROMI.

## Что начать логировать
- Tracking links: campaign / placement / creative.
- Ad registry: cost, publication_time, channel.
- Bot events: click, bot_start, lead.
- Менеджерские диалоги.
- Операционный календарь: запуски, скидки, акции.

## Ответ на 300 000 ₽
1. Пилот на 2–3 каналах.
2. Tracking links + holdout.
3. Логирование касаний и cost.
4. Через 2–4 недели — ROMI_attr и ROMI_inc.
5. Перераспределение бюджета.
6. Повторять цикл.