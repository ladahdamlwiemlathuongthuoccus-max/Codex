# Agent Codex

## Главные правила

- Отвечай на русском: коротко, профессионально, по делу.
- Рабочая папка: `D:\REDPEAK\Agent systems\Agent for Codex\Agent Codex`.
- Исходную папку `D:\REDPEAK\Agent systems\AgentHQ` не читать как рабочее состояние и не изменять.
- Все новые артефакты, проверки и память веди внутри этой копии.
- Не заявляй «готово» без свежей проверки по файлам, тестам или официальным источникам.
- Если данных не хватает, остановись и задай уточняющий вопрос.

## Codex-контур

Основной диспетчер: `codex/dispatcher.md`.

Политики:
- `codex/runtime/path-policy.md` — границы файловых изменений.
- `codex/runtime/browser-policy.md` — браузерная автоматизация и чувствительные действия.
- `codex/runtime/verification-policy.md` — проверка перед выдачей результата.

Роли:
- `codex/roles/operations-agent.md` — статусы, планы, дедлайны, координация.
- `codex/roles/legal-agent.md` — договоры, NDA, акты, юридические риски.
- `codex/roles/accounting-agent.md` — расходы, бюджет, гранты, сметы.
- `codex/roles/strategy-agent.md` — приоритеты, развилки, рекомендации.
- `codex/roles/evaluator-agent.md` — независимая проверка fact-heavy результатов.

Скиллы: `codex/skills/`.

Проверки: `codex/evals/run-codex-smoke.ps1`.

MCP/запуск: `codex/mcp/`.

## Маршрутизация

- Код, отладка, тесты, браузерные сценарии — Codex engineering mode.
- Документы `.docx`, PDF, презентации и таблицы — Codex skills/plugins: documents, pdf, presentations, spreadsheets.
- Браузерные задачи — browser-use или AgentHQ Local Control MCP, с остановкой перед чувствительным действием.
- Fact-heavy задачи — обязательный self-check и evaluator-проверка.

## Запреты

- Не писать в `D:\REDPEAK\Agent systems\AgentHQ`.
- Не писать за пределы `D:\REDPEAK\Agent systems\Agent for Codex\Agent Codex` без отдельного разрешения пользователя.
- Не использовать старые пути `D:\REDPEAK\Agent systems\AgentHQ` как активный workspace.
- Не удалять файлы без явного подтверждения.
- Не переносить Claude hooks в Codex как исполняемый runtime 1:1; использовать Codex-политики и evals.
