# Migration Inventory

Дата: 2026-04-24

## Границы

- Source reference: `D:\REDPEAK\Agent systems\AgentHQ` — только чтение.
- Working copy: `D:\REDPEAK\Agent systems\Agent for Codex\Agent Codex` — активная Codex-система.
- Изменения вне working copy запрещены без отдельного разрешения.

## Перенесённые компоненты

| Компонент Cloudy/Claude | Количество | Codex-эквивалент | Статус |
|---|---:|---|---|
| `.claude/agents/*.md` | 5 | `codex/roles/*.md` | перенесено |
| `.claude/skills/*` | 25 | `codex/skills/*` | перенесено |
| `.claude/commands/*.md` | 6 | `codex/commands/*.md` | перенесено |
| `.claude/hooks/*.py` | 12 | `codex/runtime/*` + `codex/evals/*` | заменяется политиками и smoke |
| `.mcp.json` | 1 | `.mcp.json` + `codex/mcp/*` | адаптировано под Agent Codex |
| `CLAUDE.md` | 1 | `AGENTS.md` + `codex/dispatcher.md` | legacy-reference |

## Активный Codex source-of-truth

- `AGENTS.md`
- `codex/dispatcher.md`
- `codex/runtime/path-policy.md`
- `codex/runtime/verification-policy.md`
- `codex/runtime/browser-policy.md`
- `codex/mcp/README.md`
- `codex/evals/run-codex-smoke.ps1`

## Неактивный legacy-контур

- `CLAUDE.md`
- `.claude/hooks/*`
- `.claude/settings.local.json`
- `.claude/worktrees/*`

Эти файлы оставлены для истории и сравнения. Они не должны быть source-of-truth для Codex.

