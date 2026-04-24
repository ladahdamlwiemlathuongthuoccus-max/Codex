---
name: openai-codex
description: Используй для задач по OpenAI API, Codex, Codex plugins, Codex skills, MCP-интеграции под Codex и миграции Claude/Cloudy workflow на Codex.
---

# openai-codex

## Когда использовать

- пользователь просит адаптировать агентную систему под Codex;
- нужно настроить `AGENTS.md`, Codex skills, plugins, MCP или browser-use;
- код использует OpenAI API, OpenAI SDK или Codex runtime;
- нужно заменить Claude/Anthropic-specific workflow на Codex-compatible.

## Правила

1. Для актуальных OpenAI/Codex фактов используй официальную документацию OpenAI или локальные Codex-файлы.
2. Не выдумывай параметры моделей, API и конфигов.
3. Не меняй глобальный Codex config без отдельного разрешения.
4. Любые изменения вне `Agent Codex` требуют отдельного подтверждения.

## Выход

- точный список файлов;
- проверяемый фрагмент конфигурации;
- команда smoke/eval;
- статус: PASS / BLOCKED / NEEDS_APPROVAL.

