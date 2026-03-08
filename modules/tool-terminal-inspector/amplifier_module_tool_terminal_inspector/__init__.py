"""Terminal Inspector Tool for Amplifier.

Provides dual-mode terminal application testing:
- Screen-dump mode: for Ratatui/crossterm apps with --no-alt-screen + --screen-dump-path flags
- PTY mode: universal, works with any terminal app via pyte VT100 emulation

Operations: spawn, screenshot, send_keys, send_text, find_text, wait_for_text, resize, close, list
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .keys import parse_keys, parse_keys_for_tmux
from .session_manager import PTYSession, ScreenDumpSession, SessionManager

__all__ = ["TerminalInspectorTool", "SessionManager", "mount"]

# Global session manager (lazy init on first use)
_session_manager: SessionManager | None = None
_session_manager_config: dict[str, Any] = {}


def _err(message: str) -> dict[str, Any]:
    return {"success": False, "error": message}


def _ok(output: dict[str, Any]) -> dict[str, Any]:
    return {"success": True, **output}


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        cfg = _session_manager_config
        base_dir: Path | None = None
        if raw_dir := cfg.get("session_dir"):
            base_dir = Path(str(raw_dir)).expanduser()
        _session_manager = SessionManager(
            base_dir=base_dir,
            session_timeout_minutes=int(cfg.get("session_timeout_minutes", 30)),
            default_cols=int(cfg.get("default_cols", 120)),
            default_rows=int(cfg.get("default_rows", 40)),
            default_launch_wait=float(cfg.get("default_launch_wait", 5.0)),
            default_font_size=int(cfg.get("default_font_size", 14)),
        )
    return _session_manager


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------


class TerminalInspectorTool:
    """Amplifier Tool for terminal application testing and inspection."""

    @property
    def name(self) -> str:
        return "terminal_inspector"

    @property
    def description(self) -> str:
        return (
            "Launch, interact with, and inspect terminal applications (TUI and CLI).\n\n"
            "Supports two capture modes:\n"
            "- dump: for Ratatui/crossterm apps with --no-alt-screen --screen-dump-path flags\n"
            "  (pixel-perfect, frame-numbered, no ANSI parsing)\n"
            "- pty: universal PTY emulation via pyte, works with any terminal app\n"
            "  (text + ANSI + PNG screenshots)\n\n"
            "Operations:\n"
            "- spawn: launch an app\n"
            "- screenshot: capture current screen state\n"
            "- send_keys: send keystrokes using {KEY} notation (e.g. 'hello{ENTER}', '{CTRL+K}')\n"
            "- send_text: send plain text without key parsing\n"
            "- find_text: search for text on screen, returns [{row, col}] positions\n"
            "- wait_for_text: poll until text appears or timeout\n"
            "- resize: resize terminal (sends SIGWINCH)\n"
            "- close: graceful shutdown (SIGTERM → 5s → SIGKILL)\n"
            "- list: list active sessions\n\n"
            "Key syntax: {ENTER} {TAB} {ESC} {UP} {DOWN} {LEFT} {RIGHT} {HOME} {END}\n"
            "{PGUP} {PGDN} {F1}-{F12} {CTRL+A}-{CTRL+Z} {BACKSPACE} {DELETE} {SPACE}\n\n"
            "Typical flow: spawn → wait_for_text (ready gate) → screenshot → send_keys → "
            "wait_for_text → screenshot → close"
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "spawn", "screenshot", "send_keys", "send_text",
                        "find_text", "wait_for_text", "resize", "close", "list",
                    ],
                    "description": "Operation to perform",
                },
                "session_id": {
                    "type": "string",
                    "description": "Session ID (required for all ops except spawn and list)",
                },
                "command": {
                    "type": "string",
                    "description": "Command to run (required for spawn)",
                },
                "mode": {
                    "type": "string",
                    "enum": ["auto", "dump", "pty"],
                    "description": (
                        "Capture mode: 'dump' for Ratatui apps with --screen-dump-path, "
                        "'pty' for any terminal app, 'auto' (default) detects from command"
                    ),
                    "default": "auto",
                },
                "keys": {
                    "type": "string",
                    "description": (
                        "Keystrokes to send, with {KEY} notation for special keys. "
                        "E.g. 'Hello!{ENTER}', '{CTRL+K}', '{UP}{UP}{ENTER}'"
                    ),
                },
                "text": {
                    "type": "string",
                    "description": (
                        "Plain text to send (send_text) or search for (find_text, wait_for_text). "
                        "No {KEY} parsing — use this when text contains braces."
                    ),
                },
                "settle_s": {
                    "type": "number",
                    "description": "Seconds to wait after sending keys (default: 0.15)",
                    "default": 0.15,
                },
                "rows": {
                    "type": "integer",
                    "description": "Terminal height in rows (spawn default: 40, also used for resize)",
                    "default": 40,
                },
                "cols": {
                    "type": "integer",
                    "description": "Terminal width in columns (spawn default: 120, also used for resize)",
                    "default": 120,
                },
                "launch_wait": {
                    "type": "number",
                    "description": (
                        "Seconds to wait after spawn for initial render (default: 5.0). "
                        "Set higher for slow-starting apps (amplifier TUI needs ~12s)"
                    ),
                },
                "timeout_s": {
                    "type": "number",
                    "description": "Timeout for wait_for_text in seconds (default: 10.0)",
                    "default": 10.0,
                },
                "poll_s": {
                    "type": "number",
                    "description": "Poll interval for wait_for_text in seconds (default: 0.2)",
                    "default": 0.2,
                },
            },
            "required": ["operation"],
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        operation = input.get("operation")
        if not operation:
            return _err("Missing required parameter: operation")

        manager = get_session_manager()

        try:
            match operation:
                case "spawn":
                    return await self._spawn(manager, input)
                case "screenshot":
                    return await self._screenshot(manager, input)
                case "send_keys":
                    return await self._send_keys(manager, input)
                case "send_text":
                    return await self._send_text(manager, input)
                case "find_text":
                    return self._find_text(manager, input)
                case "wait_for_text":
                    return self._wait_for_text(manager, input)
                case "resize":
                    return self._resize(manager, input)
                case "close":
                    return await self._close(manager, input)
                case "list":
                    return self._list(manager)
                case _:
                    return _err(f"Unknown operation: {operation}")
        except Exception as exc:  # noqa: BLE001
            return _err(f"Operation '{operation}' failed: {exc}")

    # -- Operations ----------------------------------------------------------

    async def _spawn(self, manager: SessionManager, inp: dict) -> dict[str, Any]:
        command = inp.get("command")
        if not command:
            return _err("Missing required parameter: command")

        session = await manager.spawn(
            command=command,
            mode=inp.get("mode", "auto"),
            rows=inp.get("rows"),
            cols=inp.get("cols"),
            launch_wait=inp.get("launch_wait"),
        )

        return _ok({
            "session_id": session.id,
            "mode": "dump" if isinstance(session, ScreenDumpSession) else "pty",
            "command": command,
            "rows": session.rows,
            "cols": session.cols,
            "status": "running" if session.is_alive() else "exited",
        })

    async def _screenshot(self, manager: SessionManager, inp: dict) -> dict[str, Any]:
        session_id = inp.get("session_id")
        if not session_id:
            return _err("Missing required parameter: session_id")
        session = manager.get(session_id)
        if not session:
            return _err(f"Session not found: {session_id}")

        if isinstance(session, ScreenDumpSession):
            snap = session.screenshot()
        else:
            snap = await session.screenshot()

        return _ok(snap)

    async def _send_keys(self, manager: SessionManager, inp: dict) -> dict[str, Any]:
        session_id = inp.get("session_id")
        if not session_id:
            return _err("Missing required parameter: session_id")
        session = manager.get(session_id)
        if not session:
            return _err(f"Session not found: {session_id}")

        keys = inp.get("keys", "")
        settle_s = float(inp.get("settle_s", 0.15))

        if isinstance(session, ScreenDumpSession):
            segments = parse_keys_for_tmux(keys)
            session.send_keys(segments, settle_s=settle_s)
        else:
            key_bytes = parse_keys(keys)
            await session.send(key_bytes, wait_ms=int(settle_s * 1000))

        return _ok({"status": "sent", "keys": keys, "alive": session.is_alive()})

    async def _send_text(self, manager: SessionManager, inp: dict) -> dict[str, Any]:
        session_id = inp.get("session_id")
        if not session_id:
            return _err("Missing required parameter: session_id")
        session = manager.get(session_id)
        if not session:
            return _err(f"Session not found: {session_id}")

        text = inp.get("text", "")
        settle_s = float(inp.get("settle_s", 0.15))

        if isinstance(session, ScreenDumpSession):
            import subprocess, time  # noqa: E401
            subprocess.run(
                ["tmux", "send-keys", "-t", session.tmux_session, "-l", text],
                capture_output=True, check=False,
            )
            time.sleep(settle_s)
        else:
            await session.send(text.encode("utf-8"), wait_ms=int(settle_s * 1000))

        return _ok({"status": "sent", "text": text, "alive": session.is_alive()})

    def _find_text(self, manager: SessionManager, inp: dict) -> dict[str, Any]:
        session_id = inp.get("session_id")
        if not session_id:
            return _err("Missing required parameter: session_id")
        session = manager.get(session_id)
        if not session:
            return _err(f"Session not found: {session_id}")

        text = inp.get("text", "")
        positions = manager.find_text(session, text)
        return _ok({"positions": positions, "found": len(positions) > 0, "text": text})

    def _wait_for_text(self, manager: SessionManager, inp: dict) -> dict[str, Any]:
        session_id = inp.get("session_id")
        if not session_id:
            return _err("Missing required parameter: session_id")
        session = manager.get(session_id)
        if not session:
            return _err(f"Session not found: {session_id}")

        text = inp.get("text", "")
        timeout_s = float(inp.get("timeout_s", 10.0))
        poll_s = float(inp.get("poll_s", 0.2))
        result = manager.wait_for_text(session, text, timeout_s=timeout_s, poll_s=poll_s)
        return _ok(result)

    def _resize(self, manager: SessionManager, inp: dict) -> dict[str, Any]:
        session_id = inp.get("session_id")
        if not session_id:
            return _err("Missing required parameter: session_id")
        session = manager.get(session_id)
        if not session:
            return _err(f"Session not found: {session_id}")

        old_rows, old_cols = session.rows, session.cols
        rows = inp.get("rows", old_rows)
        cols = inp.get("cols", old_cols)
        session.resize(rows, cols)
        return _ok({
            "status": "resized",
            "old_size": {"rows": old_rows, "cols": old_cols},
            "new_size": {"rows": rows, "cols": cols},
            "alive": session.is_alive(),
        })

    async def _close(self, manager: SessionManager, inp: dict) -> dict[str, Any]:
        session_id = inp.get("session_id")
        if not session_id:
            return _err("Missing required parameter: session_id")
        closed = await manager.close(session_id)
        if closed:
            return _ok({"status": "closed", "session_id": session_id})
        return _err(f"Session not found: {session_id}")

    def _list(self, manager: SessionManager) -> dict[str, Any]:
        sessions = manager.list_sessions()
        return _ok({
            "sessions": [
                {
                    "session_id": s.id,
                    "command": s.command,
                    "mode": "dump" if isinstance(s, ScreenDumpSession) else "pty",
                    "status": "running" if s.is_alive() else "exited",
                    "rows": s.rows,
                    "cols": s.cols,
                    "created_at": s.created_at.isoformat(),
                }
                for s in sessions
            ],
            "count": len(sessions),
        })


# ---------------------------------------------------------------------------
# Amplifier module mount point
# ---------------------------------------------------------------------------


async def mount(coordinator: Any, config: dict[str, Any]) -> TerminalInspectorTool:
    """Mount the terminal_inspector tool onto the Amplifier coordinator.

    Args:
        coordinator: Amplifier coordinator for tool registration
        config: Configuration from behaviors/terminal-tester.yaml. Keys:
            session_dir: Base directory for session data (default: ~/.amplifier/terminal-sessions)
            session_timeout_minutes: Auto-cleanup timeout (default: 30)
            default_cols: Default terminal width (default: 120)
            default_rows: Default terminal height (default: 40)
            default_launch_wait: Default wait after spawn in seconds (default: 5.0)
            default_font_size: Font size for PNG screenshots (default: 14)

    Returns:
        The mounted tool instance.
    """
    global _session_manager_config
    _session_manager_config = config or {}

    tool = TerminalInspectorTool()
    await coordinator.mount("tools", tool, name="terminal_inspector")
    return tool
