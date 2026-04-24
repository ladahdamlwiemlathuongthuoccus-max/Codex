from __future__ import annotations

import ctypes
import ctypes.wintypes
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(
    os.environ.get("AGENT_CODEX_ROOT", str(PLUGIN_ROOT.parent.parent))
).resolve()
BROWSER_PLUGIN_ROOT = Path(
    os.environ.get("AGENT_CODEX_BROWSER_ROOT", str(PROJECT_ROOT / "codex" / "browser"))
).resolve()
STATE_ROOT = PLUGIN_ROOT / "state"
SCREENSHOT_ROOT = STATE_ROOT / "screenshots"
RUN_ROOT = STATE_ROOT / "runs"

for path in (STATE_ROOT, SCREENSHOT_ROOT, RUN_ROOT):
    path.mkdir(parents=True, exist_ok=True)

mcp = FastMCP(
    "AgentHQ Local Control",
    instructions=(
        "Local MCP server for Windows app control and browser automation on the user's laptop. "
        "Use prepare/review before sensitive submissions."
    ),
    json_response=True,
)


def _import_pywinauto():
    from pywinauto import Desktop, keyboard, mouse

    return Desktop, keyboard, mouse


def _import_image_grab():
    from PIL import ImageGrab

    return ImageGrab


def _run_subprocess(command: list[str], cwd: Path | None = None) -> dict[str, Any]:
    process = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "command": command,
        "cwd": str(cwd) if cwd else None,
        "returncode": process.returncode,
        "stdout": process.stdout.strip(),
        "stderr": process.stderr.strip(),
    }


def _resolve_user_path(value: str | None, *, default_parent: Path | None = None) -> Path | None:
    if not value:
        return None
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    if default_parent:
        return (default_parent / candidate).resolve()
    return (PROJECT_ROOT / candidate).resolve()


def _window_to_dict(wrapper: Any) -> dict[str, Any]:
    element = wrapper.element_info
    rectangle = wrapper.rectangle()
    return {
        "handle": int(element.handle or 0),
        "title": element.name or "",
        "className": element.class_name or "",
        "controlType": getattr(element, "control_type", "") or "",
        "automationId": getattr(element, "automation_id", "") or "",
        "processId": getattr(element, "process_id", None),
        "isVisible": bool(wrapper.is_visible()),
        "isEnabled": bool(wrapper.is_enabled()),
        "rectangle": {
            "left": rectangle.left,
            "top": rectangle.top,
            "right": rectangle.right,
            "bottom": rectangle.bottom,
        },
    }


def _get_desktop():
    Desktop, _, _ = _import_pywinauto()
    return Desktop(backend="uia")


class _Win32Rect:
    def __init__(self, left: int, top: int, right: int, bottom: int) -> None:
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom


class _Win32ElementInfo:
    def __init__(self, handle: int, name: str, class_name: str, process_id: int) -> None:
        self.handle = handle
        self.name = name
        self.class_name = class_name
        self.control_type = "Window"
        self.automation_id = ""
        self.process_id = process_id


class _Win32Window:
    def __init__(self, handle: int, title: str, class_name: str, process_id: int) -> None:
        self.element_info = _Win32ElementInfo(handle, title, class_name, process_id)
        self._handle = handle
        self._title = title

    def rectangle(self) -> _Win32Rect:
        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(self._handle, ctypes.byref(rect))
        return _Win32Rect(rect.left, rect.top, rect.right, rect.bottom)

    def is_visible(self) -> bool:
        return bool(ctypes.windll.user32.IsWindowVisible(self._handle))

    def is_enabled(self) -> bool:
        return bool(ctypes.windll.user32.IsWindowEnabled(self._handle))

    def window_text(self) -> str:
        return self._title


def _enumerate_windows_win32(visible_only: bool = True) -> list[Any]:
    windows: list[Any] = []
    user32 = ctypes.windll.user32

    enum_proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(handle: int, _lparam: int) -> bool:
        if visible_only and not user32.IsWindowVisible(handle):
            return True

        length = user32.GetWindowTextLengthW(handle)
        title_buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(handle, title_buffer, length + 1)
        title = title_buffer.value

        class_buffer = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(handle, class_buffer, 256)

        process_id = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(process_id))

        if title:
            windows.append(_Win32Window(int(handle), title, class_buffer.value, int(process_id.value)))
        return True

    user32.EnumWindows(enum_proc_type(callback), 0)
    return windows


def _enumerate_windows(visible_only: bool = True) -> list[Any]:
    try:
        windows = _get_desktop().windows()
    except Exception:
        return _enumerate_windows_win32(visible_only=visible_only)
    if visible_only:
        visible = []
        for window in windows:
            try:
                if window.is_visible():
                    visible.append(window)
            except Exception:
                continue
        windows = visible
    return windows


def _match_text(actual: str, expected: str | None) -> bool:
    if not expected:
        return True
    return expected.lower() in (actual or "").lower()


def _find_window(window_handle: int | None = None, title_contains: str | None = None, index: int = 0) -> Any:
    if window_handle is not None:
        return _get_desktop().window(handle=window_handle).wrapper_object()

    matches = [window for window in _enumerate_windows(True) if _match_text(window.window_text(), title_contains)]
    if not matches:
        raise RuntimeError(f"No window found for title filter: {title_contains!r}")
    if index >= len(matches):
        raise RuntimeError(f"Window index {index} out of range for filter {title_contains!r}")
    return matches[index]


def _walk_controls(wrapper: Any, depth: int, max_depth: int, limit: int, results: list[dict[str, Any]]) -> None:
    if len(results) >= limit or depth > max_depth:
        return

    for child in wrapper.children():
        if len(results) >= limit:
            return
        try:
            meta = _window_to_dict(child)
            meta["depth"] = depth
            results.append(meta)
            _walk_controls(child, depth + 1, max_depth, limit, results)
        except Exception:
            continue


def _resolve_control(
    window_handle: int,
    control_handle: int | None = None,
    title: str | None = None,
    auto_id: str | None = None,
    control_type: str | None = None,
    index: int = 0,
) -> Any:
    desktop = _get_desktop()
    if control_handle is not None:
        return desktop.window(handle=control_handle).wrapper_object()

    window = _find_window(window_handle=window_handle)
    matches = []
    for control in window.descendants():
        element = control.element_info
        if not _match_text(element.name or "", title):
            continue
        if not _match_text(getattr(element, "automation_id", "") or "", auto_id):
            continue
        if not _match_text(getattr(element, "control_type", "") or "", control_type):
            continue
        matches.append(control)

    if not matches:
        raise RuntimeError("No matching control found.")
    if index >= len(matches):
        raise RuntimeError(f"Control index {index} out of range.")
    return matches[index]


def _capture_image(window_handle: int | None = None, full_desktop: bool = False, output_path: Path | None = None) -> dict[str, Any]:
    ImageGrab = _import_image_grab()
    if output_path is None:
        output_path = SCREENSHOT_ROOT / f"screenshot-{time.strftime('%Y%m%d-%H%M%S')}.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if full_desktop or window_handle is None:
        image = ImageGrab.grab(all_screens=True)
    else:
        window = _find_window(window_handle=window_handle)
        rectangle = window.rectangle()
        bbox = (rectangle.left, rectangle.top, rectangle.right, rectangle.bottom)
        image = ImageGrab.grab(bbox=bbox, all_screens=True)

    image.save(output_path)
    return {"path": str(output_path), "size": image.size}


def _foreground_window_handle() -> int:
    handle = ctypes.windll.user32.GetForegroundWindow()
    return int(handle)


def _ensure_browser_runtime(install_chromium: bool = True) -> dict[str, Any]:
    if not BROWSER_PLUGIN_ROOT.exists():
        raise RuntimeError(f"Browser runtime plugin not found at {BROWSER_PLUGIN_ROOT}")

    result = {"steps": []}
    node_modules = BROWSER_PLUGIN_ROOT / "node_modules"
    if not node_modules.exists():
        step = _run_subprocess(["npm", "install"], cwd=BROWSER_PLUGIN_ROOT)
        result["steps"].append(step)
        if step["returncode"] != 0:
            raise RuntimeError(f"npm install failed: {step['stderr']}")

    if install_chromium:
        executable_check = _run_subprocess(
            ["node", "-e", "const { chromium } = require('playwright'); process.stdout.write(chromium.executablePath());"],
            cwd=BROWSER_PLUGIN_ROOT,
        )
        result["steps"].append(executable_check)
        browser_path = executable_check["stdout"]
        if executable_check["returncode"] != 0 or not browser_path or not Path(browser_path).exists():
            install_step = _run_subprocess(["npx", "playwright", "install", "chromium"], cwd=BROWSER_PLUGIN_ROOT)
            result["steps"].append(install_step)
            if install_step["returncode"] != 0:
                raise RuntimeError(f"playwright install chromium failed: {install_step['stderr']}")

    result["browserPluginRoot"] = str(BROWSER_PLUGIN_ROOT)
    return result


def _browser_executable_candidates(browser: str) -> list[Path]:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    program_files = Path(os.environ.get("ProgramFiles", ""))
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", ""))

    if browser == "msedge":
        return [
            program_files / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            program_files_x86 / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        ]

    return [
        local / "Google" / "Chrome" / "Application" / "chrome.exe",
        program_files / "Google" / "Chrome" / "Application" / "chrome.exe",
        program_files_x86 / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]


def _find_browser_executable(browser: str) -> Path:
    for candidate in _browser_executable_candidates(browser):
        if candidate.exists():
            return candidate
    raise RuntimeError(f"Browser executable not found for {browser}")


@mcp.tool()
def server_status() -> dict[str, Any]:
    """Get local runtime status for the MCP server and its browser dependency."""
    return {
        "pluginRoot": str(PLUGIN_ROOT),
        "projectRoot": str(PROJECT_ROOT),
        "browserPluginRoot": str(BROWSER_PLUGIN_ROOT),
        "pythonExecutable": os.sys.executable,
        "windowsUiAvailable": True,
        "browserRuntimePresent": BROWSER_PLUGIN_ROOT.exists(),
        "browserNodeModulesPresent": (BROWSER_PLUGIN_ROOT / "node_modules").exists(),
    }


@mcp.tool()
def launch_app(command: str, arguments: list[str] | None = None, cwd: str | None = None, wait_seconds: int = 2) -> dict[str, Any]:
    """Launch a Windows application or script."""
    arguments = arguments or []
    resolved_cwd = _resolve_user_path(cwd)
    process = subprocess.Popen(
        [command, *arguments],
        cwd=str(resolved_cwd) if resolved_cwd else None,
    )
    if wait_seconds > 0:
        time.sleep(wait_seconds)
    return {
        "pid": process.pid,
        "command": command,
        "arguments": arguments,
        "cwd": str(resolved_cwd) if resolved_cwd else None,
    }


@mcp.tool()
def terminate_app(pid: int) -> dict[str, Any]:
    """Terminate an application by PID."""
    os.kill(pid, 9)
    return {"terminated": True, "pid": pid}


@mcp.tool()
def list_windows(title_contains: str | None = None, visible_only: bool = True, limit: int = 20) -> list[dict[str, Any]]:
    """List visible Windows application windows."""
    windows = _enumerate_windows(visible_only=visible_only)
    matches = [window for window in windows if _match_text(window.window_text(), title_contains)]
    return [_window_to_dict(window) for window in matches[:limit]]


@mcp.tool()
def get_active_window() -> dict[str, Any]:
    """Get the currently focused window."""
    handle = _foreground_window_handle()
    window = _find_window(window_handle=handle)
    return _window_to_dict(window)


@mcp.tool()
def focus_window(window_handle: int) -> dict[str, Any]:
    """Focus a window by its native handle."""
    window = _find_window(window_handle=window_handle)
    window.set_focus()
    return {"focused": True, "window": _window_to_dict(window)}


@mcp.tool()
def inspect_window(window_handle: int, max_depth: int = 2, limit: int = 100) -> dict[str, Any]:
    """Inspect a window and return a flattened subset of its UI tree."""
    window = _find_window(window_handle=window_handle)
    controls: list[dict[str, Any]] = []
    _walk_controls(window, depth=1, max_depth=max_depth, limit=limit, results=controls)
    return {
        "window": _window_to_dict(window),
        "controls": controls,
    }


@mcp.tool()
def click_control(
    window_handle: int,
    control_handle: int | None = None,
    title: str | None = None,
    auto_id: str | None = None,
    control_type: str | None = None,
    index: int = 0,
    double: bool = False,
) -> dict[str, Any]:
    """Click a UI control inside a window."""
    window = _find_window(window_handle=window_handle)
    window.set_focus()
    control = _resolve_control(
        window_handle=window_handle,
        control_handle=control_handle,
        title=title,
        auto_id=auto_id,
        control_type=control_type,
        index=index,
    )
    if double:
        control.double_click_input()
    else:
        control.click_input()
    return {"clicked": True, "control": _window_to_dict(control)}


@mcp.tool()
def set_text(
    window_handle: int,
    text: str,
    control_handle: int | None = None,
    title: str | None = None,
    auto_id: str | None = None,
    control_type: str | None = None,
    index: int = 0,
    append: bool = False,
    press_enter: bool = False,
) -> dict[str, Any]:
    """Set or type text into a control."""
    _, keyboard, _ = _import_pywinauto()
    window = _find_window(window_handle=window_handle)
    window.set_focus()
    control = _resolve_control(
        window_handle=window_handle,
        control_handle=control_handle,
        title=title,
        auto_id=auto_id,
        control_type=control_type,
        index=index,
    )
    control.set_focus()

    if hasattr(control, "set_edit_text") and not append:
        control.set_edit_text(text)
    else:
        control.click_input()
        if not append:
            keyboard.send_keys("^a{BACKSPACE}", pause=0.02)
        keyboard.send_keys(text, with_spaces=True, pause=0.02)

    if press_enter:
        keyboard.send_keys("{ENTER}", pause=0.02)

    return {"updated": True, "control": _window_to_dict(control), "textLength": len(text)}


@mcp.tool()
def press_keys(keys: str, window_handle: int | None = None) -> dict[str, Any]:
    """Send key presses to the focused window or to a specific window after focusing it."""
    _, keyboard, _ = _import_pywinauto()
    if window_handle is not None:
        _find_window(window_handle=window_handle).set_focus()
    keyboard.send_keys(keys, with_spaces=True, pause=0.02)
    return {"sent": True, "keys": keys, "windowHandle": window_handle}


@mcp.tool()
def click_coordinates(x: int, y: int, button: str = "left", double: bool = False) -> dict[str, Any]:
    """Click at desktop coordinates."""
    _, _, mouse = _import_pywinauto()
    if double:
        mouse.double_click(button=button, coords=(x, y))
    else:
        mouse.click(button=button, coords=(x, y))
    return {"clicked": True, "x": x, "y": y, "button": button, "double": double}


@mcp.tool()
def scroll(amount: int, x: int | None = None, y: int | None = None) -> dict[str, Any]:
    """Scroll mouse wheel at an optional position."""
    _, _, mouse = _import_pywinauto()
    coords = (x, y) if x is not None and y is not None else None
    mouse.scroll(wheel_dist=amount, coords=coords)
    return {"scrolled": True, "amount": amount, "coords": coords}


@mcp.tool()
def capture_screenshot(
    output_path: str | None = None,
    window_handle: int | None = None,
    full_desktop: bool = False,
) -> dict[str, Any]:
    """Capture a desktop or window screenshot."""
    resolved_output = _resolve_user_path(output_path, default_parent=PROJECT_ROOT)
    return _capture_image(window_handle=window_handle, full_desktop=full_desktop, output_path=resolved_output)


@mcp.tool()
def browser_prepare_runtime(install_chromium: bool = True) -> dict[str, Any]:
    """Install npm and Playwright browser runtime dependencies used by browser scenarios."""
    return _ensure_browser_runtime(install_chromium=install_chromium)


@mcp.tool()
def open_browser_url(
    url: str,
    profile_name: str = "default",
    browser: str = "chrome",
    new_window: bool = True,
) -> dict[str, Any]:
    """Open a URL in a real browser with a persistent profile for manual login or review."""
    executable = _find_browser_executable(browser)
    profile_dir = BROWSER_PLUGIN_ROOT / "state" / "profiles" / profile_name
    profile_dir.mkdir(parents=True, exist_ok=True)

    command = [str(executable), f"--user-data-dir={profile_dir}"]
    if new_window:
        command.append("--new-window")
    command.append(url)

    process = subprocess.Popen(command)
    return {
        "pid": process.pid,
        "browser": browser,
        "url": url,
        "profileDir": str(profile_dir),
        "executable": str(executable),
    }


@mcp.tool()
def run_browser_scenario(
    scenario_path: str,
    output_dir: str | None = None,
    browser: str = "chromium",
    channel: str | None = None,
    profile_name: str | None = None,
    headless: bool = False,
    allow_sensitive: bool = False,
    install_chromium: bool = True,
) -> dict[str, Any]:
    """Run a Playwright browser scenario through the repo-owned browser runtime."""
    _ensure_browser_runtime(install_chromium=install_chromium and browser == "chromium")

    scenario = _resolve_user_path(scenario_path, default_parent=PROJECT_ROOT)
    if not scenario or not scenario.exists():
        raise RuntimeError(f"Scenario not found: {scenario_path}")

    resolved_output = _resolve_user_path(output_dir, default_parent=PROJECT_ROOT)
    if resolved_output is None:
        resolved_output = RUN_ROOT / f"browser-run-{time.strftime('%Y%m%d-%H%M%S')}"
    resolved_output.mkdir(parents=True, exist_ok=True)

    command = [
        "node",
        str(BROWSER_PLUGIN_ROOT / "scripts" / "browser-runner.mjs"),
        "--scenario",
        str(scenario),
        "--browser",
        browser,
        "--output-dir",
        str(resolved_output),
    ]

    if channel:
        command.extend(["--channel", channel])
    if headless:
        command.extend(["--headless", "true"])
    if allow_sensitive:
        command.extend(["--allow-sensitive", "true"])
    if profile_name:
        profile_dir = BROWSER_PLUGIN_ROOT / "state" / "profiles" / profile_name
        profile_dir.mkdir(parents=True, exist_ok=True)
        command.extend(["--profile-dir", str(profile_dir)])

    result = _run_subprocess(command, cwd=BROWSER_PLUGIN_ROOT)
    summary_path = resolved_output / "browser-run-summary.json"
    payload = {
        "commandResult": result,
        "outputDir": str(resolved_output),
        "summaryPath": str(summary_path),
    }
    if summary_path.exists():
        payload["summary"] = json.loads(summary_path.read_text(encoding="utf-8"))
    return payload


if __name__ == "__main__":
    mcp.run(transport="stdio")
