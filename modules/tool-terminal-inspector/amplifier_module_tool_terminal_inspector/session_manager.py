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
import os
import shutil
import signal
import struct
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# keys.py is a required sibling module (it has no external deps beyond `re`,
# so unlike the soft-imports below it is not optional on any platform).
# `parse_keys` is reused by the dump-mode ConPTY backend's send_keys() to
# turn a tmux key name back into real terminal bytes -- see
# _TMUX_NAME_TO_CANONICAL below for why that's a safe, lossless translation.
from .keys import TMUX_KEY_NAMES, parse_keys

# fcntl/pty/select/termios are POSIX-only and back PTY mode exclusively (the
# read loop, the fork, and both resize paths). They are soft-imported for the
# same reason pyte is below: dump mode does not touch them, so a platform that
# lacks them should lose PTY mode -- not the whole module.
#
# Caught on ImportError rather than gated on sys.platform deliberately. A
# platform check says "not Windows, proceed" and then still dies on a
# POSIX-shaped environment that happens to lack these modules (a locked-down
# container, a restricted embedded runtime). Asking the import whether it
# worked is the question we actually care about.
try:
    import fcntl
    import pty
    import select
    import termios

    _HAS_PTY_SUPPORT = True
except ImportError:
    _HAS_PTY_SUPPORT = False

# winpty (pywinpty) backs PTY mode on native Windows via ConPTY. Soft-imported
# for the same reason as the POSIX block above: its absence should cost PTY
# mode, not the whole module. The two backends are mutually exclusive in
# practice (POSIX platforms won't have pywinpty installed and vice versa),
# but both are probed independently rather than gated on sys.platform, for
# the same "ask the import, don't guess the platform" reasoning as above.
try:
    import winpty

    _HAS_CONPTY = True
except ImportError:
    _HAS_CONPTY = False

# Single derived predicate PTY dispatch actually branches on. POSIX is
# preferred when both are somehow present, since this module was POSIX-first
# and POSIX behavior must remain byte-identical to before ConPTY support was
# added. `None` means neither backend is usable on this platform.
if _HAS_PTY_SUPPORT:
    _PTY_BACKEND: str | None = "posix"
elif _HAS_CONPTY:
    _PTY_BACKEND = "conpty"
else:
    _PTY_BACKEND = None

# tmux backs dump mode's process-host role by default (see ScreenDumpSession
# and SessionManager._spawn_dump below). tmux is invoked via subprocess, not
# imported, so there's no "try: import tmux" to hang a soft-import off of the
# way the blocks above do for pywinpty/pyte/Pillow -- shutil.which() is the
# equivalent presence probe. As with those probes, this is independent of
# platform: any box that happens to lack tmux (Windows or otherwise) behaves
# the same way.
_HAS_TMUX = shutil.which("tmux") is not None

# Single derived predicate dump-mode dispatch actually branches on -- same
# shape and reasoning as _PTY_BACKEND above. tmux is preferred when both are
# somehow present, since dump mode was tmux-first and tmux behavior must
# remain byte-identical to before ConPTY support was added. `None` means
# neither backend is usable on this platform.
if _HAS_TMUX:
    _DUMP_BACKEND: str | None = "tmux"
elif _HAS_CONPTY:
    _DUMP_BACKEND = "conpty"
else:
    _DUMP_BACKEND = None

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
    """Whether a tmux session named `name` currently exists.

    check=False already makes this tolerant of a *nonzero exit* (no session
    by that name). But when the tmux binary itself isn't installed at all
    (every native Windows box, and any POSIX box without it), subprocess.run
    raises FileNotFoundError before any returncode exists -- and that's not
    an error condition here: if tmux isn't installed, no tmux session
    exists, so returning False is the semantically correct answer, not a
    workaround.
    """
    try:
        r = subprocess.run(
            ["tmux", "has-session", "-t", name],
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return r.returncode == 0


def _run_tmux(*args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(["tmux", *args], capture_output=True, text=True, check=True)
    except FileNotFoundError as e:
        # Only the "binary doesn't exist" case is translated -- a tmux
        # command that ran and failed (check=True raising
        # CalledProcessError) is a real tmux-level error and must keep
        # propagating unmodified, not be swallowed here.
        raise RuntimeError(
            "tmux is not installed or not on PATH (dump-mode's tmux-backed "
            "process host requires it). tmux has no native Windows build; "
            "on native Windows use ConPTY-backed dump mode (requires the "
            "winpty package) or PTY mode instead."
        ) from e


# Reverse of keys.TMUX_KEY_NAMES: tmux key name -> one canonical {KEY} name
# that produces it, so the ConPTY dump-mode backend can turn a tmux-style
# named-key segment (already parsed by keys.parse_keys_for_tmux() before it
# ever reaches this module) back into real terminal bytes via
# keys.parse_keys(), instead of hand-rolling a second key table. Several
# canonical names collide on the same tmux name (e.g. TAB and CTRL+I both
# map to "Tab"; ENTER/RETURN/CTRL+M all map to "Enter"), but every such
# collision produces byte-identical output from keys.SPECIAL_KEYS, so
# picking any one name back out of a collision is safe -- no fidelity is
# actually lost. Derived mechanically from keys.py's own table at import
# time, not a second hand-maintained mapping.
_TMUX_NAME_TO_CANONICAL: dict[str, str] = {tmux_name: canonical for canonical, tmux_name in TMUX_KEY_NAMES.items()}


# ---------------------------------------------------------------------------
# Session dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ScreenDumpSession:
    """A terminal session driven via screen-dump file capture.

    Screen capture itself is backend-agnostic: the app under test writes its
    own render buffer to `dump_path` via --screen-dump-path, and
    `_parse_dump()`/`wait_for_dump()`/`screenshot()` just read that file --
    neither of those needs to know or care which backend is hosting the
    process. Only process lifecycle (alive check, keystroke delivery,
    resize, teardown) differs, chosen at spawn time via `backend`:
      - "tmux": tmux session + send-keys (the original implementation)
      - "conpty": winpty.PtyProcess, for native Windows where tmux has no
        build

    `tmux_session` doubles as a plain session-identifier string on the
    conpty backend (nothing looks it up as an actual tmux session there).
    `conpty_proc` is only meaningful when backend == "conpty".
    """

    id: str
    command: str
    rows: int
    cols: int
    tmux_session: str
    dump_path: str
    session_dir: Path
    backend: str = "tmux"
    conpty_proc: Any = None  # winpty.PtyProcess; set only when backend == "conpty"
    created_at: datetime = field(default_factory=datetime.now)

    def is_alive(self) -> bool:
        if self.backend == "conpty":
            return bool(self.conpty_proc is not None and self.conpty_proc.isalive())
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
        """Send keystroke segments to the underlying process.

        segments: list of (is_literal, value) from parse_keys_for_tmux() --
        the tool layer always parses via parse_keys_for_tmux() regardless of
        backend, so on the conpty branch a non-literal segment's `value` is
        a tmux key name (e.g. "Enter", "C-k"), not a {KEY} token. That name
        is translated back to real terminal bytes via _TMUX_NAME_TO_CANONICAL
        + keys.parse_keys() rather than via tmux itself.
        """
        if self.backend == "conpty":
            for is_literal, value in segments:
                if is_literal:
                    text = value
                else:
                    canonical = _TMUX_NAME_TO_CANONICAL.get(value)
                    if canonical is not None:
                        data = parse_keys(f"{{{canonical}}}")
                    else:
                        # Unrecognized tmux name -- fall back to sending it
                        # literally, mirroring parse_keys()'s own
                        # unknown-key "pass through as text" behavior.
                        data = value.encode("utf-8")
                    # PtyProcess.write() takes str, not bytes -- same
                    # str/bytes asymmetry handled the same way in
                    # PTYSession.send()'s conpty branch.
                    text = data.decode("utf-8", errors="replace")
                self.conpty_proc.write(text)
            time.sleep(settle_s)
            return
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
        """Resize the underlying process's terminal (app sees SIGWINCH-equivalent)."""
        self.rows = rows
        self.cols = cols
        if self.backend == "conpty":
            if self.conpty_proc is not None:
                self.conpty_proc.setwinsize(rows, cols)
            return
        _run_tmux("resize-window", "-t", self.tmux_session, "-x", str(cols), "-y", str(rows))

    def close(self) -> None:
        """Kill the underlying process/session and clean up dump files."""
        if self.backend == "conpty":
            try:
                if self.conpty_proc is not None:
                    self.conpty_proc.terminate(force=True)
                    self.conpty_proc.close()
            except Exception:  # noqa: BLE001 -- pywinpty's exception types on an
                # already-dead process vary by version; closing is best-effort,
                # same reasoning as PTYSession.close()'s conpty branch.
                pass
        elif _tmux_session_exists(self.tmux_session):
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


def _conpty_reader_loop(proc: Any, buffer: list[str], lock: threading.Lock) -> None:
    """Background thread body: continuously drain a ConPTY process's output.

    pywinpty has no select()-equivalent for readiness polling -- proc.read()
    simply blocks until data or EOF. So instead of the POSIX branch's
    "poll readiness, then read" loop, a single daemon thread blocks on
    proc.read() in a loop and appends whatever comes back to a shared list.
    PTYSession._read_output_conpty() drains that list on a bounded timer;
    this thread never touches pyte or the session object directly, and never
    blocks anything but itself.
    """
    while True:
        try:
            if not proc.isalive():
                break
            chunk = proc.read()
        except Exception:  # noqa: BLE001 -- EOFError and pywinpty's own exception
            # types both just mean "the process is done producing output";
            # this thread's only job is to stop cleanly when that happens.
            break
        if not chunk:
            break
        with lock:
            buffer.append(chunk)


def _conpty_discard_reader_loop(proc: Any) -> None:
    """Background thread body: drain a dump-mode ConPTY process's output and discard it.

    Screen-dump mode gets its screen content from the app's own dump file
    (see _parse_dump/screenshot), never from the process's own stdout -- so
    unlike PTY mode's _conpty_reader_loop, there is no buffer for this to
    feed and no pyte stream to keep fed. But the OS-level pipe backing a
    ConPTY still has to be read from by *someone*, or a chatty app under
    test can fill the pipe buffer and block on its own writes -- the same
    backpressure problem _conpty_reader_loop exists to avoid, just with
    nowhere here to put the output. This thread's only job is to keep that
    pipe drained so the app under test never blocks on it.
    """
    while True:
        try:
            if not proc.isalive():
                break
            chunk = proc.read()
        except Exception:  # noqa: BLE001 -- same reasoning as _conpty_reader_loop:
            # EOFError and pywinpty's own exception types both just mean
            # "the process is done producing output"; this thread's only
            # job is to stop cleanly when that happens.
            break
        if not chunk:
            break


@dataclass
class PTYSession:
    """A terminal session via PTY spawn + pyte VT100 emulation.

    Backed by one of two backends, chosen at spawn time (see `backend`):
      - "posix": pty.fork() + a raw fd (the original, POSIX-only implementation)
      - "conpty": winpty.PtyProcess, for native Windows via ConPTY

    `pid`/`fd` are only meaningful for the posix backend. `conpty_proc` and
    the private `_conpty_*` reader-thread fields are only meaningful for the
    conpty backend. Both backends share `screen`/`stream` (pyte) and every
    public method on this class (is_alive/resize/close/send/screenshot/etc).
    """

    id: str
    command: str
    rows: int
    cols: int
    screen: Any  # pyte.Screen
    stream: Any  # pyte.Stream
    session_dir: Path
    pid: int = -1
    fd: int = -1
    backend: str = "posix"
    conpty_proc: Any = None  # winpty.PtyProcess; set only when backend == "conpty"
    created_at: datetime = field(default_factory=datetime.now)
    capture_count: int = 0
    font_size: int = 14
    # ConPTY reader-thread state (see _conpty_reader_loop / _read_output_conpty).
    # Unused, and left as None, on the posix backend.
    _conpty_buffer: Any = field(default=None, repr=False, compare=False)
    _conpty_lock: Any = field(default=None, repr=False, compare=False)
    _conpty_reader_thread: Any = field(default=None, repr=False, compare=False)

    def is_alive(self) -> bool:
        if self.backend == "conpty":
            return bool(self.conpty_proc is not None and self.conpty_proc.isalive())
        try:
            os.kill(self.pid, 0)
            return True
        except OSError:
            return False

    def _read_output(self, timeout: float = 0.1, max_reads: int = 100) -> bytes:
        if self.backend == "conpty":
            return self._read_output_conpty(timeout, max_reads)
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

    def _drain_conpty_buffer(self) -> list[str]:
        """Atomically pop everything the reader thread has accumulated so far."""
        with self._conpty_lock:
            if not self._conpty_buffer:
                return []
            drained = list(self._conpty_buffer)
            self._conpty_buffer.clear()
            return drained

    def _read_output_conpty(self, timeout: float, max_reads: int) -> bytes:
        """ConPTY read loop: drains the background reader thread's buffer.

        There is no select()-equivalent for a ConPTY handle in pywinpty, so
        this can't poll readiness per-chunk the way the POSIX branch does.
        Instead: check the buffer once; if nothing is there yet, wait up to
        `timeout` seconds (bounded -- never blocks indefinitely) and check
        once more, then return whatever is available either way. This
        mirrors the POSIX branch's "select() times out -> stop" behavior
        with a single wait instead of a per-chunk poll. `max_reads` is
        accepted for signature parity with the posix branch but the conpty
        reader thread already batches everything it has read, so there is
        nothing further to gain from looping past the first successful drain.
        """
        del max_reads  # not meaningful for the buffer-draining model above
        chunks = self._drain_conpty_buffer()
        if not chunks:
            time.sleep(timeout)
            chunks = self._drain_conpty_buffer()
        text = "".join(chunks)
        if text:
            # NOTE: PtyProcess.read() already returns decoded str (unlike
            # POSIX os.read(), which returns bytes and is decoded explicitly
            # above) -- `text` here is NOT bytes that need decoding. Feeding
            # it straight into pyte, and encoding it below only so this
            # method's return type matches the posix branch's, is correct.
            # Do NOT call .decode() on anything in this method.
            self.stream.feed(text)
        return text.encode("utf-8", errors="replace")

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
        if self.backend == "conpty":
            # PtyProcess.write() takes str, not bytes -- the same str/bytes
            # asymmetry as the read side (see _read_output_conpty), just in
            # the opposite direction: decode here instead of encoding.
            self.conpty_proc.write(data.decode("utf-8", errors="replace"))
        else:
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
        """Resize the PTY and notify the child of the new size."""
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
            if self.backend == "conpty":
                self.conpty_proc.setwinsize(rows, cols)
            else:
                winsize = struct.pack("HHHH", rows, cols, 0, 0)
                fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)
                os.kill(self.pid, signal.SIGWINCH)

    def close(self) -> None:
        """Close the session and terminate the child process."""
        if self.backend == "conpty":
            # PtyProcess has no separate "close the fd" step -- terminate()
            # covers what os.close(self.fd) + SIGTERM/SIGKILL do together on
            # POSIX. force=True mirrors this method's POSIX fallback to
            # SIGKILL after a graceful-termination window.
            try:
                if self.conpty_proc is not None:
                    self.conpty_proc.terminate(force=True)
                    self.conpty_proc.close()
            except Exception:  # noqa: BLE001 -- pywinpty's exception types on an
                # already-dead process vary by version; closing is best-effort.
                pass
            return
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
            if _DUMP_BACKEND is None:
                raise RuntimeError(
                    "Dump mode is unavailable: no usable process-host backend was "
                    "found on this platform. Dump mode needs either tmux (not "
                    "found on PATH here) or, on native Windows, the winpty "
                    "package for ConPTY support -- install it with: "
                    "pip install pywinpty. PTY mode is the other capture mode "
                    "and does not need tmux."
                )
            session = await self._spawn_dump(session_id, command, rows, cols, session_dir, wait)
        else:
            if _PTY_BACKEND is None:
                raise RuntimeError(
                    "PTY mode is unavailable: no usable PTY backend was found on "
                    "this platform. POSIX platforms need fcntl/pty/select/termios "
                    "(these should always be present -- a locked-down container or "
                    "restricted runtime may be missing them). Native Windows needs "
                    "the winpty package for ConPTY support -- install it with: "
                    "pip install pywinpty. Dump mode is the other capture mode; it "
                    "also needs tmux or winpty (the same two backends), so it will "
                    "be unavailable here too without one of the above."
                )
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
        session_name = f"terminal-inspector-{session_id}"
        dump_path = str(session_dir / "screen.txt")

        # If command already specifies --screen-dump-path, use it; otherwise inject
        if "--screen-dump-path" not in command:
            command = f"{command} --no-alt-screen --screen-dump-path {dump_path}"

        # Extract dump_path from command if already specified
        if "--screen-dump-path" in command:
            parts = command.split("--screen-dump-path")
            if len(parts) > 1:
                dump_path = parts[1].strip().split()[0]

        if _DUMP_BACKEND == "conpty":
            return await self._spawn_dump_conpty(
                session_id, session_name, command, rows, cols, session_dir, dump_path, launch_wait
            )

        # tmux backend (unchanged from the original implementation)
        # Create tmux session
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", session_name, "-x", str(cols), "-y", str(rows)],
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["tmux", "send-keys", "-t", session_name, command, "Enter"],
            capture_output=True,
            check=True,
        )

        session = ScreenDumpSession(
            id=session_id,
            command=command,
            rows=rows,
            cols=cols,
            tmux_session=session_name,
            dump_path=dump_path,
            session_dir=session_dir,
        )

        # Wait for the dump file to appear (initial render)
        if launch_wait > 0:
            session.wait_for_dump(timeout=launch_wait + 5.0)

        return session

    async def _spawn_dump_conpty(
        self,
        session_id: str,
        session_name: str,
        command: str,
        rows: int,
        cols: int,
        session_dir: Path,
        dump_path: str,
        launch_wait: float,
    ) -> ScreenDumpSession:
        """Spawn a screen-dump session via ConPTY (native Windows) using pywinpty.

        Capture is unaffected: `command` (with --no-alt-screen
        --screen-dump-path already appended by the caller, exactly as for
        the tmux branch) is the same command a tmux-hosted session would
        run, and the app under test writes its own render buffer to
        `dump_path` exactly the same way either way -- see the class
        docstring on ScreenDumpSession. ConPTY only replaces tmux's role as
        the PROCESS HOST: what starts the command, delivers keystrokes,
        reports whether it's alive, resizes it, and tears it down (the
        `backend` branches on ScreenDumpSession).

        Unlike PTY mode's ConPTY spawn, there is no pyte stream to feed and
        nothing here ever reads process output for content -- but the
        ConPTY's output pipe still needs draining or a chatty app can block
        on its own writes, so a background thread (_conpty_discard_reader_loop)
        does that and throws the output away.
        """
        argv = ["cmd.exe", "/c", command]
        proc = winpty.PtyProcess.spawn(  # type: ignore[union-attr]
            argv,
            # Mirrors the PTY-mode conpty spawn: fork() implicitly inherits
            # cwd on the tmux/posix branches, so it's passed explicitly here.
            cwd=os.getcwd(),
            env=os.environ.copy(),
            dimensions=(rows, cols),
        )

        reader_thread = threading.Thread(
            target=_conpty_discard_reader_loop,
            args=(proc,),
            daemon=True,
        )
        reader_thread.start()

        session = ScreenDumpSession(
            id=session_id,
            command=command,
            rows=rows,
            cols=cols,
            tmux_session=session_name,
            dump_path=dump_path,
            session_dir=session_dir,
            backend="conpty",
            conpty_proc=proc,
        )

        # Wait for the dump file to appear (initial render) -- identical to
        # the tmux branch; the app under test writes the file regardless of
        # which backend is hosting the process.
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
        if _PTY_BACKEND == "conpty":
            return await self._spawn_pty_conpty(session_id, command, rows, cols, session_dir)

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

    async def _spawn_pty_conpty(
        self,
        session_id: str,
        command: str,
        rows: int,
        cols: int,
        session_dir: Path,
    ) -> PTYSession:
        """Spawn a PTY session via ConPTY (native Windows) using pywinpty.

        Mirrors `_spawn_pty`'s POSIX behavior everywhere the backend allows:
        the same TERM/COLUMNS/LINES env injection, the same initial pyte
        screen/stream, the same initial-output pump before returning. What
        differs is dictated by the backend, not by choice:
          - the command runs through `cmd.exe /c` instead of `/bin/sh -c`
          - there is no fork()/fd; PtyProcess.spawn() hands back a process
            object with no select()-style readiness signal for its output,
            so a daemon reader thread (started here) continuously drains it
            into a buffer that PTYSession._read_output_conpty() polls
        """
        spawn_env = os.environ.copy()
        spawn_env["TERM"] = "xterm-256color"
        spawn_env["COLUMNS"] = str(cols)
        spawn_env["LINES"] = str(rows)

        screen = pyte.Screen(cols, rows)  # type: ignore[attr-defined]
        stream = pyte.Stream(screen)  # type: ignore[attr-defined]

        argv = ["cmd.exe", "/c", command]
        proc = winpty.PtyProcess.spawn(  # type: ignore[union-attr]
            argv,
            # Mirrors the POSIX branch, which inherits the current working
            # directory implicitly via fork() -- there is no fork() here, so
            # it has to be passed explicitly to get the same behavior.
            cwd=os.getcwd(),
            env=spawn_env,
            dimensions=(rows, cols),
        )

        # See _conpty_reader_loop's docstring: pywinpty has no select()
        # equivalent, so a background thread drains proc.read() into this
        # buffer instead of the read loop polling readiness per-chunk.
        conpty_buffer: list[str] = []
        conpty_lock = threading.Lock()
        reader_thread = threading.Thread(
            target=_conpty_reader_loop,
            args=(proc, conpty_buffer, conpty_lock),
            daemon=True,
        )
        reader_thread.start()

        session = PTYSession(
            id=session_id,
            command=command,
            rows=rows,
            cols=cols,
            screen=screen,
            stream=stream,
            session_dir=session_dir,
            backend="conpty",
            conpty_proc=proc,
            font_size=self.default_font_size,
        )
        session._conpty_buffer = conpty_buffer
        session._conpty_lock = conpty_lock
        session._conpty_reader_thread = reader_thread

        # Initial output pump (mirrors the POSIX branch above)
        await asyncio.sleep(0.5)
        await session.pump_output(duration=0.5)
        return session

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
