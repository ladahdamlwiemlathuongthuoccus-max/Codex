import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.stdout.reconfigure(encoding="utf-8")


def extract_content(result):
    try:
        if hasattr(result, "model_dump"):
            return result.model_dump(mode="json")
    except Exception:
        pass
    return str(result)


async def main() -> int:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parents[2]
    python_exe = Path(
        os.environ.get(
            "AGENTHQ_LOCAL_CONTROL_PYTHON",
            r"C:\Users\sashatrash\.codex\plugins\cache\local\agenthq-local-control\1.0.0\.venv\Scripts\python.exe",
        )
    )
    server_path = script_dir / "agenthq_local_control_mcp.py"
    server_params = StdioServerParameters(
        command=str(python_exe),
        args=[str(server_path)],
        env={
            "PYTHONUTF8": "1",
            "AGENT_CODEX_ROOT": str(project_root),
            "AGENT_CODEX_BROWSER_ROOT": str(project_root / "codex" / "browser"),
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            status = await session.call_tool("server_status", {})
            windows = await session.call_tool("list_windows", {"limit": 5})

    payload = {
        "toolCount": len(tools.tools),
        "tools": [tool.name for tool in tools.tools],
        "serverStatus": extract_content(status),
        "windows": extract_content(windows),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
