---
description: Недельный брифинг — operations ‖ accounting → strategy. Параллельно статус и burn rate, потом стратегический анализ поверх.
---

# /weekly-brief

Формирование недельного брифинга для руководителя.

## Параллельные задачи (operations ‖ accounting)

1. **operations-agent** — статус за прошедшую неделю, топ-приоритеты на следующую, активные блокеры, open risks. Загрузи: `memory: obligations (актуальные)`, `operations/risk_log.md`, `operations/session_markers.md` последние записи.

2. **accounting-agent** — burn rate за неделю, план-факт по открытым обязательствам, остаток гранта ФСИ (если есть факты). Загрузи: `finance/`, `memory: obligations (финансовые)`, `documents/grants/`.

Запусти оба субагента ПАРАЛЛЕЛЬНО (один Task-вызов с несколькими Agent в одном сообщении).

## Последовательно (strategy поверх)

3. **strategy-agent** — возьми результаты operations и accounting, добавь стратегический слой по режиму «Еженедельный брифинг» из своего промпта:
   - Фокус недели (одна главная задача)
   - Точечные рекомендации (3–5)
   - Упущенные возможности
   - Ранние сигналы рисков
   - Вопрос руководителю
   - Блок «Эволюция системы» (данные из calibration_log)

## Evaluator (при флаге EVALUATOR_AGENT_ENABLED)

После strategy — запустить `evaluator-agent` на итоговом документе. Это fact-heavy задача.

## Формат результата

Итоговый markdown-документ. Сохранить в `operations/weekly_brief_YYYY-MM-DD.md`.

## Верификация

- Все цифры имеют источник (путь к файлу или ID записи памяти)
- `strategy` получил данные из `operations` И `accounting` (не придумал)
- `evaluator` выдал PASS (или NEEDS_FIX с указанием, что исправить)
