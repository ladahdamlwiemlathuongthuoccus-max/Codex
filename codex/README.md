# Agent Codex Runtime

Это Codex-адаптация агентной системы RedPeak.

## Source of Truth

- `AGENTS.md` — правила Codex для проекта.
- `codex/dispatcher.md` — маршрутизация задач, роли, проверки, правила инструментов.
- `codex/roles/` — адаптированные роли из Cloudy/Claude-контура.
- `codex/skills/` — рабочие навыки и шаблоны.
- `codex/commands/` — частые рабочие сценарии.
- `codex/runtime/` — bootstrap и политики выполнения.
- `codex/mcp/` — MCP-конфигурация для Codex.
- `codex/browser/` — безопасные browser smoke assets/scenarios.
- `codex/evals/` — smoke/eval-проверки.

## Что изменено относительно Cloudy/Claude

- Активный workspace заменён на `D:\REDPEAK\Agent systems\Agent for Codex\Agent Codex`.
- Claude hooks не считаются активным runtime. Их функции перенесены в Codex-политики и evals.
- Anthropic document skills заменены на Codex skills/plugins: documents, pdf, presentations, spreadsheets.
- Browser workflows выполняются через browser-use / AgentHQ Local Control MCP с ручным подтверждением чувствительных действий.
- Старый `CLAUDE.md` оставлен как исторический reference, но не является главным правилом для Codex.
- Любые изменения вне `Agent Codex` требуют отдельного разрешения пользователя.

## Быстрая проверка

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\codex\evals\run-codex-smoke.ps1
```
