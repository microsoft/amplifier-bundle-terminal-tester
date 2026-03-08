"""Session manager for terminal inspector tool.

Supports two capture modes:

1. Screen-dump mode (for Ratatui/crossterm apps):
   - Launch in a tmux session with --no-alt-screen --screen-dump-path flags
   - Reads the app's own render buffer from a file after every frame
   - Frame numbers enable precise render-completion detection
   - Uses tmux send-keys for keystroke delivery

2. PTY mode (universal, for any terminal app):
   - Forks a pseudo-terminal, runs the app directly
   - Uses pyte VT100 emulation to maintain a virtual screen buffer
   - Captures as text, ANSI color output, and PNG via Pillow
   - Based on Diego Colombo's amplifier-bundle-tui-tester implementation

Auto-detection: if command contains '--screen-dump-path', dump mode is used.
Otherwise PTY mode.
"""

from __future__ import annotations

import asyncio
import fcntl
import os
import pty
import select
import signal
import struct
import subprocess
import termios
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# pyte is required for PTY mode; soft-import so dump mode still works without it
try:
    import pyte

    _HAS_PYTE = True
except ImportError:
    _HAS_PYTE = False

# Pillow is required for PNG screenshots in PTY mode
try:
    from PIL import Image, ImageDraw, ImageFont

    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


# ---------------------------------------------------------------------------
# Color helpers (PTY mode / PNG generation)
# ---------------------------------------------------------------------------

_NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "red": (205, 49, 49),
    "green": (13, 188, 121),
    "yellow": (229, 229, 16),
    "blue": (36, 114, 200),
    "magenta": (188, 63, 188),
    "cyan": (17, 168, 205),
    "white": (229, 229, 229),
}

_BRIGHT_NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "black": (102, 102, 102),
    "red": (241, 76, 76),
    "green": (35, 209, 139),
    "yellow": (245, 245, 67),
    "blue": (59, 142, 234),
    "magenta": (214, 112, 214),
    "cyan": (41, 184, 219),
    "white": (255, 255, 255),
}

_STANDARD_INDEX_NAMES = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
_CUBE_VALUES: list[int] = [0, 95, 135, 175, 215, 255]
_DEFAULT_FG: tuple[int, int, int] = (220, 220, 220)
_DEFAULT_BG: tuple[int, int, int] = (30, 30, 30)


def _xterm_256_to_rgb(n: int) -> tuple[int, int, int]:
    if n < 0 or n > 255:
        return _DEFAULT_FG
    if n < 8:
        return _NAMED_COLORS[_STANDARD_INDEX_NAMES[n]]
    if n < 16:
        return _BRIGHT_NAMED_COLORS[_STANDARD_INDEX_NAMES[n - 8]]
    if n < 232:
        idx = n - 16
        return (_CUBE_VALUES[idx // 36], _CUBE_VALUES[(idx // 6) % 6], _CUBE_VALUES[idx % 6])
    value = 8 + (n - 232) * 10
    return (value, value, value)


def _resolve_color(raw: str, default: tuple[int, int, int]) -> tuple[int, int, int]:
    if not raw or raw == "default":
        return default
    if raw in _NAMED_COLORS:
        return _NAMED_COLORS[raw]
    try:
        idx = int(raw)
        if 0 <= idx <= 255:
            return _xterm_256_to_rgb(idx)
    except (ValueError, TypeError):
        pass
    if isinstance(raw, str) and len(raw) == 6:
        try:
            return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))
        except ValueError:
            pass
    return default


def _brighten(color: tuple[int, int, int], amount: int = 50) -> tuple[int, int, int]:
    return (min(color[0] + amount, 255), min(color[1] + amount, 255), min(color[2] + amount, 255))


_FONT_SEARCH_PATHS: list[str] = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "/usr/share/fonts/liberation-mono/LiberationMono-Regular.ttf",
    "/System/Library/Fonts/Monaco.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "/Library/Fonts/SF-Mono-Regular.otf",
    "C:\\Windows\\Fonts\\consola.ttf",
]


def _load_monospace_font(size: int) -> Any:
    if not _HAS_PIL:
        return None
    for fp in _FONT_SEARCH_PATHS:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Screen-dump mode helpers
# ---------------------------------------------------------------------------


def _parse_dump(path: str) -> tuple[int, list[str]]:
    """Parse a screen dump file written by the TUI's --screen-dump-path feature.

    Format:
        FRAME <N>
        SIZE <cols>x<rows>
        <row0 content>
        <row1 content>
        ...

    Returns (frame_number, lines).  frame_number is -1 on parse failure.
    """
    try:
        with open(path) as f:
            text = f.read()
    except OSError:
        return (-1, [])

    lines = text.splitlines()
    if len(lines) < 2:
        return (-1, [])

    frame_number = -1
    if lines[0].startswith("FRAME "):
        try:
            frame_number = int(lines[0].split()[1])
        except (IndexError, ValueError):
            pass

    return (frame_number, lines[2:])  # Skip FRAME + SIZE header lines


def _tmux_session_exists(name: str) -> bool:
    r = subprocess.run(
        ["tmux", "has-session", "-t", name],
        capture_output=True,
        check=False,
    )
    return r.returncode == 0


def _run_tmux(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["tmux", *args], capture_output=True, text=True, check=True)


# ---------------------------------------------------------------------------
# Session dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ScreenDumpSession:
    """A terminal session driven via tmux + screen-dump file capture."""

    id: str
    command: str
    rows: int
    cols: int
    tmux_session: str
    dump_path: str
    session_dir: Path
    created_at: datetime = field(default_factory=datetime.now)

    def is_alive(self) -> bool:
        return _tmux_session_exists(self.tmux_session)

    def screenshot(self) -> dict[str, Any]:
        """Read current screen state from the dump file."""
        frame, lines = _parse_dump(self.dump_path)

        # Trim trailing blank rows
        while lines and not lines[-1].strip():
            lines.pop()

        text = "\n".join(lines)
        return {
            "text": text,
            "frame": frame,
            "rows": self.rows,
            "cols": self.cols,
            "image_path": None,  # not available in dump mode
            "alive": self.is_alive(),
        }

    def send_keys(self, segments: list[tuple[bool, str]], settle_s: float = 0.15) -> None:
        """Send keystroke segments via tmux send-keys.

        segments: list of (is_literal, value) from parse_keys_for_tmux()
        """
        for is_literal, value in segments:
            if is_literal:
                _run_tmux("send-keys", "-t", self.tmux_session, "-l", value)
            else:
                _run_tmux("send-keys", "-t", self.tmux_session, value)
        time.sleep(settle_s)

    def wait_for_dump(self, timeout: float = 20.0, poll: float = 0.2) -> bool:
        """Block until the dump file appears with at least one frame."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            frame, lines = _parse_dump(self.dump_path)
            if frame >= 0 and lines:
                return True
            time.sleep(poll)
        return False

    def resize(self, rows: int, cols: int) -> None:
        """Resize the tmux window (app sees SIGWINCH via tmux)."""
        self.rows = rows
        self.cols = cols
        _run_tmux("resize-window", "-t", self.tmux_session, "-x", str(cols), "-y", str(rows))

    def close(self) -> None:
        """Kill the tmux session and clean up dump files."""
        if _tmux_session_exists(self.tmux_session):
            subprocess.run(
                ["tmux", "kill-session", "-t", self.tmux_session],
                capture_output=True,
                check=False,
            )
        for path in [self.dump_path, self.dump_path + ".tmp"]:
            try:
                os.unlink(path)
            except OSError:
                pass


@dataclass
class PTYSession:
    """A terminal session via PTY fork + pyte VT100 emulation."""

    id: str
    command: str
    rows: int
    cols: int
    pid: int
    fd: int
    screen: Any  # pyte.Screen
    stream: Any  # pyte.Stream
    session_dir: Path
    created_at: datetime = field(default_factory=datetime.now)
    capture_count: int = 0
    font_size: int = 14

    def is_alive(self) -> bool:
        try:
            os.kill(self.pid, 0)
            return True
        except OSError:
            return False

    def _read_output(self, timeout: float = 0.1, max_reads: int = 100) -> bytes:
        output = bytearray()
        reads = 0
        while reads < max_reads:
            reads += 1
            ready, _, _ = select.select([self.fd], [], [], timeout)
            if not ready:
                break
            try:
                chunk = os.read(self.fd, 8192)
                if not chunk:
                    break
                output.extend(chunk)
                self.stream.feed(chunk.decode("utf-8", errors="replace"))
            except OSError:
                break
        return bytes(output)

    async def pump_output(self, duration: float = 0.5, poll: float = 0.05) -> bytes:
        """Drain PTY output for `duration` seconds to let async TUIs finish rendering."""
        output = bytearray()
        end_time = time.monotonic() + duration
        loop = asyncio.get_event_loop()
        while time.monotonic() < end_time:
            chunk = await loop.run_in_executor(None, self._read_output, poll, 10)
            if chunk:
                output.extend(chunk)
            await asyncio.sleep(poll)
        return bytes(output)

    async def send(self, data: bytes, wait_ms: int = 150) -> None:
        """Write bytes to the PTY and pump output."""
        os.write(self.fd, data)
        await asyncio.sleep(wait_ms / 1000.0)
        self._read_output()

    async def screenshot(self) -> dict[str, Any]:
        """Capture current PTY state as text, ANSI, and PNG."""
        await self.pump_output(duration=0.5, poll=0.05)

        text_lines = [line.rstrip() for line in self.screen.display]
        text = "\n".join(text_lines)

        image_path: str | None = None
        if _HAS_PIL:
            self.capture_count += 1
            img_path = self.session_dir / f"capture_{self.capture_count:04d}.png"
            self._render_image(img_path)
            image_path = str(img_path)

        return {
            "text": text,
            "frame": -1,  # not available in PTY mode
            "rows": self.rows,
            "cols": self.cols,
            "image_path": image_path,
            "alive": self.is_alive(),
        }

    def _render_image(self, path: Path, font_size: int | None = None) -> None:
        """Render the pyte screen buffer to a PNG file."""
        if not _HAS_PIL:
            return
        size = font_size or self.font_size
        padding = 10
        font = _load_monospace_font(size)

        try:
            bbox = font.getbbox("M")  # type: ignore[union-attr]
            char_width = bbox[2] - bbox[0]
            char_height = max(bbox[3] - bbox[1], size) + 2
        except Exception:  # noqa: BLE001
            char_width, char_height = 8, size + 2

        img_w = self.cols * char_width + padding * 2
        img_h = self.rows * char_height + padding * 2

        image = Image.new("RGB", (img_w, img_h), _DEFAULT_BG)  # type: ignore[union-attr]
        draw = ImageDraw.Draw(image)  # type: ignore[union-attr]

        for row_idx, row in enumerate(self.screen.buffer.values()):
            y = padding + row_idx * char_height
            for col_idx in range(self.cols):
                char_data = row.get(col_idx)
                if char_data is None:
                    continue
                x = padding + col_idx * char_width
                bg = _resolve_color(char_data.bg, _DEFAULT_BG)
                if bg != _DEFAULT_BG:
                    draw.rectangle([x, y, x + char_width, y + char_height], fill=bg)
                fg = _resolve_color(char_data.fg, _DEFAULT_FG)
                if char_data.bold:
                    fg = _brighten(fg)
                ch = char_data.data if char_data.data else " "
                draw.text((x, y), ch, fill=fg, font=font)

        # Draw cursor
        cx, cy = self.screen.cursor.x, self.screen.cursor.y
        draw.rectangle(
            [padding + cx * char_width, padding + cy * char_height,
             padding + (cx + 1) * char_width, padding + (cy + 1) * char_height],
            outline=(100, 100, 200),
        )

        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path, "PNG")

    def resize(self, rows: int, cols: int) -> None:
        """Resize the PTY and notify the child via SIGWINCH."""
        old_display = list(self.screen.display)
        new_screen = pyte.Screen(cols, rows)  # type: ignore[attr-defined]
        new_stream = pyte.Stream(new_screen)  # type: ignore[attr-defined]
        # Copy visible text to new screen
        for row_idx, line in enumerate(old_display):
            if row_idx >= rows:
                break
            for col_idx, ch in enumerate(line):
                if col_idx >= cols:
                    break
                if ch != " ":
                    cell = new_screen.buffer[row_idx].get(col_idx, new_screen.default_char)
                    new_screen.buffer[row_idx][col_idx] = cell._replace(data=ch)
        self.screen = new_screen
        self.stream = new_stream
        self.rows = rows
        self.cols = cols
        if self.is_alive():
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)
            os.kill(self.pid, signal.SIGWINCH)

    def close(self) -> None:
        """Close the PTY fd and terminate the child process."""
        try:
            os.close(self.fd)
        except OSError:
            pass
        if self.is_alive():
            try:
                os.kill(self.pid, signal.SIGTERM)
                for _ in range(50):  # up to 5s
                    try:
                        os.waitpid(self.pid, os.WNOHANG)
                        os.kill(self.pid, 0)
                        time.sleep(0.1)
                    except OSError:
                        return
                os.kill(self.pid, signal.SIGKILL)
            except OSError:
                pass


# Union type for either session kind
TerminalSession = ScreenDumpSession | PTYSession


# ---------------------------------------------------------------------------
# SessionManager
# ---------------------------------------------------------------------------


class SessionManager:
    """Manages terminal sessions for the terminal_inspector tool.

    Supports both screen-dump (Ratatui) and PTY (universal) sessions.
    """

    def __init__(
        self,
        base_dir: Path | None = None,
        session_timeout_minutes: int = 30,
        default_cols: int = 120,
        default_rows: int = 40,
        default_launch_wait: float = 5.0,
        default_font_size: int = 14,
    ) -> None:
        if base_dir is None:
            base_dir = Path.home() / ".amplifier" / "terminal-sessions"
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.session_timeout_minutes = session_timeout_minutes
        self.default_cols = default_cols
        self.default_rows = default_rows
        self.default_launch_wait = default_launch_wait
        self.default_font_size = default_font_size
        self._sessions: dict[str, TerminalSession] = {}

    # -- Session discovery ---------------------------------------------------

    def _detect_mode(self, command: str, mode: str) -> str:
        """Auto-detect capture mode from command string."""
        if mode != "auto":
            return mode
        if "--screen-dump-path" in command:
            return "dump"
        return "pty"

    # -- Lifecycle -----------------------------------------------------------

    async def spawn(
        self,
        command: str,
        mode: str = "auto",
        rows: int | None = None,
        cols: int | None = None,
        launch_wait: float | None = None,
    ) -> TerminalSession:
        """Spawn a new terminal session and return it."""
        self._cleanup_stale()

        session_id = uuid.uuid4().hex[:8]
        session_dir = self.base_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        rows = rows or self.default_rows
        cols = cols or self.default_cols
        wait = launch_wait if launch_wait is not None else self.default_launch_wait
        effective_mode = self._detect_mode(command, mode)

        if effective_mode == "dump":
            session = await self._spawn_dump(session_id, command, rows, cols, session_dir, wait)
        else:
            if not _HAS_PYTE:
                raise RuntimeError(
                    "PTY mode requires pyte. Install with: pip install pyte"
                )
            session = await self._spawn_pty(session_id, command, rows, cols, session_dir)

        self._sessions[session_id] = session
        return session

    async def _spawn_dump(
        self,
        session_id: str,
        command: str,
        rows: int,
        cols: int,
        session_dir: Path,
        launch_wait: float,
    ) -> ScreenDumpSession:
        tmux_name = f"terminal-inspector-{session_id}"
        dump_path = str(session_dir / "screen.txt")

        # If command already specifies --screen-dump-path, use it; otherwise inject
        if "--screen-dump-path" not in command:
            command = f"{command} --no-alt-screen --screen-dump-path {dump_path}"

        # Extract dump_path from command if already specified
        if "--screen-dump-path" in command:
            parts = command.split("--screen-dump-path")
            if len(parts) > 1:
                dump_path = parts[1].strip().split()[0]

        # Create tmux session
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", tmux_name, "-x", str(cols), "-y", str(rows)],
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["tmux", "send-keys", "-t", tmux_name, command, "Enter"],
            capture_output=True,
            check=True,
        )

        session = ScreenDumpSession(
            id=session_id,
            command=command,
            rows=rows,
            cols=cols,
            tmux_session=tmux_name,
            dump_path=dump_path,
            session_dir=session_dir,
        )

        # Wait for the dump file to appear (initial render)
        if launch_wait > 0:
            session.wait_for_dump(timeout=launch_wait + 5.0)

        return session

    async def _spawn_pty(
        self,
        session_id: str,
        command: str,
        rows: int,
        cols: int,
        session_dir: Path,
    ) -> PTYSession:
        spawn_env = os.environ.copy()
        spawn_env["TERM"] = "xterm-256color"
        spawn_env["COLUMNS"] = str(cols)
        spawn_env["LINES"] = str(rows)

        screen = pyte.Screen(cols, rows)  # type: ignore[attr-defined]
        stream = pyte.Stream(screen)  # type: ignore[attr-defined]

        pid, fd = pty.fork()

        if pid == 0:
            # Child: exec the command
            os.execvpe("/bin/sh", ["/bin/sh", "-c", command], spawn_env)
        else:
            # Parent: set window size
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

            session = PTYSession(
                id=session_id,
                command=command,
                rows=rows,
                cols=cols,
                pid=pid,
                fd=fd,
                screen=screen,
                stream=stream,
                session_dir=session_dir,
                font_size=self.default_font_size,
            )

            # Initial output pump
            await asyncio.sleep(0.5)
            await session.pump_output(duration=0.5)
            return session

        raise RuntimeError("Child process failed to exec")  # pragma: no cover

    # -- Public API ----------------------------------------------------------

    def get(self, session_id: str) -> TerminalSession | None:
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[TerminalSession]:
        self._cleanup_stale()
        return list(self._sessions.values())

    async def close(self, session_id: str) -> bool:
        session = self._sessions.pop(session_id, None)
        if session:
            session.close()
            return True
        return False

    async def close_all(self) -> int:
        ids = list(self._sessions.keys())
        count = 0
        for sid in ids:
            if await self.close(sid):
                count += 1
        return count

    # -- Cleanup -------------------------------------------------------------

    def _cleanup_stale(self) -> int:
        cutoff = datetime.now() - timedelta(minutes=self.session_timeout_minutes)
        stale = [sid for sid, s in self._sessions.items() if s.created_at < cutoff]
        for sid in stale:
            session = self._sessions.pop(sid, None)
            if session:
                session.close()
        return len(stale)

    # -- Text operations (work for both session types) -----------------------

    def find_text(self, session: TerminalSession, text: str) -> list[dict[str, int]]:
        """Search for text on the session screen.

        Returns list of {row, col} positions (1-based).
        """
        if isinstance(session, ScreenDumpSession):
            _, lines = _parse_dump(session.dump_path)
        else:
            lines = [line.rstrip() for line in session.screen.display]

        positions = []
        for row_idx, line in enumerate(lines, start=1):
            col = 0
            while True:
                pos = line.find(text, col)
                if pos == -1:
                    break
                positions.append({"row": row_idx, "col": pos + 1})
                col = pos + 1
        return positions

    def wait_for_text(
        self,
        session: TerminalSession,
        text: str,
        timeout_s: float = 10.0,
        poll_s: float = 0.2,
    ) -> dict[str, Any]:
        """Poll until text appears on screen or timeout expires.

        Returns {found, elapsed_s, text}.
        """
        start = time.monotonic()
        deadline = start + timeout_s
        while time.monotonic() < deadline:
            positions = self.find_text(session, text)
            if positions:
                return {"found": True, "elapsed_s": time.monotonic() - start, "text": text}
            time.sleep(poll_s)
        return {"found": False, "elapsed_s": time.monotonic() - start, "text": text}
