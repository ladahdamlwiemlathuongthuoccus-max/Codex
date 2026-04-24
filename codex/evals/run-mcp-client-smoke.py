from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = ROOT / "codex" / "evals" / "runs" / f"mcp-client-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


def resolve_args(args: list[str]) -> list[str]:
    resolved: list[str] = []
    for index, arg in enumerate(args):
        candidate = Path(arg)
        if index == 0 and not candidate.is_absolute():
            resolved.append(str((ROOT / candidate).resolve()))
        else:
            resolved.append(str(candidate if candidate.is_absolute() else arg))
    return resolved


def dump_result(result: Any) -> Any:
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    return str(result)


async def test_server(name: str, entry: dict[str, Any]) -> dict[str, Any]:
    command = entry["command"]
    args = resolve_args(entry.get("args", []))
    params = StdioServerParameters(
        command=command,
        args=args,
        env={"PYTHONUTF8": "1", **os.environ},
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()

    return {
        "name": name,
        "command": command,
        "args": args,
        "toolCount": len(tools.tools),
        "tools": [tool.name for tool in tools.tools],
        "status": "PASS",
    }


async def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    config = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    reports = []
    failures = []

    for name, entry in config["mcpServers"].items():
        try:
            reports.append(await test_server(name, entry))
        except Exception as exc:  # noqa: BLE001 - smoke report must capture raw failure
            failure = {
                "name": name,
                "status": "FAIL",
                "error": str(exc),
            }
            reports.append(failure)
            failures.append(failure)

    payload = {
        "root": str(ROOT),
        "reports": reports,
        "failures": failures,
    }
    report_path = RUN_DIR / "mcp-client-smoke.json"
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

