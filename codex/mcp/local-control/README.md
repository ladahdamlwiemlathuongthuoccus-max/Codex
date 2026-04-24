# Agent Codex Local Control MCP

Project-local wrapper around the installed `agenthq-local-control` plugin.

Why this exists:

- the installed plugin runtime lives in `C:\Users\sashatrash\.codex\plugins\cache\local\agenthq-local-control\1.0.0`;
- Agent Codex must keep project state under `D:\REDPEAK\Agent systems\Agent for Codex\Agent Codex`;
- this wrapper sets `AGENT_CODEX_ROOT` and keeps the server code under the Agent Codex project.

Start script:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\codex\mcp\local-control\start-mcp.ps1
```

