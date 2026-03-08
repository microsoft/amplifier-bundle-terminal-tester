"""Tests for session_manager.py — terminal session management."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplifier_module_tool_terminal_inspector.session_manager import (
    PTYSession,
    ScreenDumpSession,
    SessionManager,
    _parse_dump,
)


# ---------------------------------------------------------------------------
# _parse_dump tests
# ---------------------------------------------------------------------------


class TestParseDump:
    """Tests for the screen dump file parser."""

    def test_parse_valid_dump(self, tmp_path: Path) -> None:
        dump = tmp_path / "screen.txt"
        dump.write_text("FRAME 42\nSIZE 120x40\nHello world\n second line\n")
        frame, lines = _parse_dump(str(dump))
        assert frame == 42
        assert lines[0] == "Hello world"
        assert lines[1] == " second line"

    def test_parse_frame_number_zero(self, tmp_path: Path) -> None:
        dump = tmp_path / "screen.txt"
        dump.write_text("FRAME 0\nSIZE 80x24\nfirst frame\n")
        frame, lines = _parse_dump(str(dump))
        assert frame == 0

    def test_parse_missing_file(self) -> None:
        frame, lines = _parse_dump("/nonexistent/path/screen.txt")
        assert frame == -1
        assert lines == []

    def test_parse_empty_file(self, tmp_path: Path) -> None:
        dump = tmp_path / "screen.txt"
        dump.write_text("")
        frame, lines = _parse_dump(str(dump))
        assert frame == -1

    def test_parse_single_line_file(self, tmp_path: Path) -> None:
        dump = tmp_path / "screen.txt"
        dump.write_text("FRAME 1\n")
        frame, lines = _parse_dump(str(dump))
        assert frame == -1  # Need at least 2 lines (FRAME + SIZE)

    def test_parse_strips_header_lines(self, tmp_path: Path) -> None:
        dump = tmp_path / "screen.txt"
        dump.write_text("FRAME 7\nSIZE 120x40\nRow 0\nRow 1\nRow 2\n")
        frame, lines = _parse_dump(str(dump))
        assert frame == 7
        assert len(lines) == 3  # FRAME and SIZE lines are stripped
        assert lines[0] == "Row 0"

    def test_parse_large_frame_number(self, tmp_path: Path) -> None:
        dump = tmp_path / "screen.txt"
        dump.write_text("FRAME 99999\nSIZE 200x50\ncontent\n")
        frame, lines = _parse_dump(str(dump))
        assert frame == 99999

    def test_parse_malformed_frame_line(self, tmp_path: Path) -> None:
        dump = tmp_path / "screen.txt"
        dump.write_text("FRAME\nSIZE 80x24\ncontent\n")
        frame, lines = _parse_dump(str(dump))
        assert frame == -1  # parse failure


# ---------------------------------------------------------------------------
# ScreenDumpSession tests
# ---------------------------------------------------------------------------


class TestScreenDumpSession:
    """Tests for ScreenDumpSession behavior."""

    def _make_session(self, tmp_path: Path, dump_content: str = "") -> ScreenDumpSession:
        dump_path = tmp_path / "screen.txt"
        if dump_content:
            dump_path.write_text(dump_content)
        return ScreenDumpSession(
            id="test-sess",
            command="./amplifier --no-alt-screen --screen-dump-path /tmp/x.txt",
            rows=40,
            cols=120,
            tmux_session="test-tmux-sess",
            dump_path=str(dump_path),
            session_dir=tmp_path,
        )

    def test_screenshot_returns_text_from_dump(self, tmp_path: Path) -> None:
        session = self._make_session(
            tmp_path,
            "FRAME 5\nSIZE 120x40\n amplifier\nconversation\n> \nEnter send\n"
        )
        snap = session.screenshot()
        assert snap["frame"] == 5
        assert "amplifier" in snap["text"]
        assert snap["rows"] == 40
        assert snap["cols"] == 120
        assert snap["image_path"] is None  # dump mode has no image

    def test_screenshot_empty_dump(self, tmp_path: Path) -> None:
        session = self._make_session(tmp_path, "")
        snap = session.screenshot()
        assert snap["frame"] == -1
        assert snap["text"] == ""

    def test_is_alive_returns_false_for_nonexistent_session(self, tmp_path: Path) -> None:
        session = self._make_session(tmp_path)
        # tmux session "test-tmux-sess" doesn't actually exist
        assert session.is_alive() is False

    def test_wait_for_dump_returns_true_when_file_ready(self, tmp_path: Path) -> None:
        dump_path = tmp_path / "screen.txt"
        session = ScreenDumpSession(
            id="test", command="cmd", rows=40, cols=120,
            tmux_session="x", dump_path=str(dump_path), session_dir=tmp_path
        )

        # Write file from a "background thread" (simulate async rendering)
        def _write_later() -> None:
            time.sleep(0.1)
            dump_path.write_text("FRAME 1\nSIZE 120x40\nhello\n")

        import threading
        t = threading.Thread(target=_write_later)
        t.start()

        result = session.wait_for_dump(timeout=3.0, poll=0.05)
        t.join()
        assert result is True

    def test_wait_for_dump_returns_false_on_timeout(self, tmp_path: Path) -> None:
        session = ScreenDumpSession(
            id="test", command="cmd", rows=40, cols=120,
            tmux_session="x",
            dump_path=str(tmp_path / "nonexistent.txt"),
            session_dir=tmp_path
        )
        result = session.wait_for_dump(timeout=0.2, poll=0.05)
        assert result is False


# ---------------------------------------------------------------------------
# SessionManager tests
# ---------------------------------------------------------------------------


class TestSessionManager:
    """Tests for SessionManager — session lifecycle management."""

    def test_init_creates_base_dir(self, tmp_path: Path) -> None:
        base = tmp_path / "sessions"
        manager = SessionManager(base_dir=base)
        assert base.exists()

    def test_get_nonexistent_session(self, tmp_path: Path) -> None:
        manager = SessionManager(base_dir=tmp_path)
        assert manager.get("nonexistent") is None

    def test_list_sessions_empty(self, tmp_path: Path) -> None:
        manager = SessionManager(base_dir=tmp_path)
        assert manager.list_sessions() == []

    def test_stale_cleanup_removes_old_sessions(self, tmp_path: Path) -> None:
        manager = SessionManager(base_dir=tmp_path, session_timeout_minutes=0)

        # Inject a fake stale session
        fake = ScreenDumpSession(
            id="stale",
            command="cmd",
            rows=24, cols=80,
            tmux_session="stale-tmux",
            dump_path="/tmp/stale.txt",
            session_dir=tmp_path / "stale",
        )
        # Force the created_at to be very old
        from datetime import datetime, timedelta
        object.__setattr__(fake, "created_at", datetime.now() - timedelta(hours=1))
        manager._sessions["stale"] = fake

        cleaned = manager._cleanup_stale()
        assert cleaned == 1
        assert manager.get("stale") is None

    def test_find_text_in_screen_dump(self, tmp_path: Path) -> None:
        dump_path = tmp_path / "screen.txt"
        dump_path.write_text(
            "FRAME 1\nSIZE 120x40\n amplifier — my-session\nHello world\n> \nEnter send\n"
        )
        session = ScreenDumpSession(
            id="s1", command="cmd", rows=40, cols=120,
            tmux_session="x", dump_path=str(dump_path), session_dir=tmp_path
        )
        manager = SessionManager(base_dir=tmp_path)
        positions = manager.find_text(session, "Enter send")
        assert len(positions) >= 1
        assert positions[0]["col"] >= 1

    def test_find_text_not_found(self, tmp_path: Path) -> None:
        dump_path = tmp_path / "screen.txt"
        dump_path.write_text("FRAME 1\nSIZE 120x40\nhello world\n")
        session = ScreenDumpSession(
            id="s1", command="cmd", rows=40, cols=120,
            tmux_session="x", dump_path=str(dump_path), session_dir=tmp_path
        )
        manager = SessionManager(base_dir=tmp_path)
        positions = manager.find_text(session, "NONEXISTENT_TEXT")
        assert positions == []

    def test_find_text_multiple_occurrences(self, tmp_path: Path) -> None:
        dump_path = tmp_path / "screen.txt"
        dump_path.write_text("FRAME 1\nSIZE 120x40\nfoo bar foo\nfoo again\n")
        session = ScreenDumpSession(
            id="s1", command="cmd", rows=40, cols=120,
            tmux_session="x", dump_path=str(dump_path), session_dir=tmp_path
        )
        manager = SessionManager(base_dir=tmp_path)
        positions = manager.find_text(session, "foo")
        assert len(positions) >= 2

    def test_wait_for_text_found_immediately(self, tmp_path: Path) -> None:
        dump_path = tmp_path / "screen.txt"
        dump_path.write_text("FRAME 1\nSIZE 120x40\nEnter send\n")
        session = ScreenDumpSession(
            id="s1", command="cmd", rows=40, cols=120,
            tmux_session="x", dump_path=str(dump_path), session_dir=tmp_path
        )
        manager = SessionManager(base_dir=tmp_path)
        result = manager.wait_for_text(session, "Enter send", timeout_s=2.0)
        assert result["found"] is True
        assert result["elapsed_s"] < 1.0

    def test_wait_for_text_timeout(self, tmp_path: Path) -> None:
        dump_path = tmp_path / "screen.txt"
        dump_path.write_text("FRAME 1\nSIZE 120x40\nhello\n")
        session = ScreenDumpSession(
            id="s1", command="cmd", rows=40, cols=120,
            tmux_session="x", dump_path=str(dump_path), session_dir=tmp_path
        )
        manager = SessionManager(base_dir=tmp_path)
        result = manager.wait_for_text(session, "NEVER_APPEARS", timeout_s=0.3, poll_s=0.05)
        assert result["found"] is False
        assert result["elapsed_s"] >= 0.3

    def test_detect_mode_dump_from_command(self, tmp_path: Path) -> None:
        manager = SessionManager(base_dir=tmp_path)
        assert manager._detect_mode(
            "./app --no-alt-screen --screen-dump-path /tmp/s.txt", "auto"
        ) == "dump"

    def test_detect_mode_pty_from_command(self, tmp_path: Path) -> None:
        manager = SessionManager(base_dir=tmp_path)
        assert manager._detect_mode("python -m my_app", "auto") == "pty"

    def test_detect_mode_explicit_override(self, tmp_path: Path) -> None:
        manager = SessionManager(base_dir=tmp_path)
        # Explicit mode overrides auto-detection
        assert manager._detect_mode("./app --screen-dump-path /tmp/x.txt", "pty") == "pty"
        assert manager._detect_mode("python app.py", "dump") == "dump"


# ---------------------------------------------------------------------------
# Integration: TerminalInspectorTool operations on screen-dump session
# ---------------------------------------------------------------------------


class TestToolWithDumpSession:
    """Tests for TerminalInspectorTool operations using a screen-dump session."""

    @pytest.fixture()
    def manager(self, tmp_path: Path) -> SessionManager:
        return SessionManager(base_dir=tmp_path)

    @pytest.fixture()
    def dump_session(self, tmp_path: Path, manager: SessionManager) -> ScreenDumpSession:
        dump_path = tmp_path / "screen.txt"
        dump_path.write_text(
            "FRAME 10\nSIZE 120x40\n amplifier\nHello\n> \nEnter send  Tab sidebar\n"
        )
        session = ScreenDumpSession(
            id="tool-test",
            command="./amplifier --no-alt-screen --screen-dump-path " + str(dump_path),
            rows=40, cols=120,
            tmux_session="tool-test-tmux",
            dump_path=str(dump_path),
            session_dir=tmp_path,
        )
        manager._sessions["tool-test"] = session
        return session

    def test_screenshot_via_manager(
        self, manager: SessionManager, dump_session: ScreenDumpSession
    ) -> None:
        session = manager.get("tool-test")
        assert session is not None
        snap = session.screenshot()
        assert snap["frame"] == 10
        assert "amplifier" in snap["text"]

    def test_find_text_via_manager(
        self, manager: SessionManager, dump_session: ScreenDumpSession
    ) -> None:
        session = manager.get("tool-test")
        positions = manager.find_text(session, "Enter send")
        assert len(positions) >= 1

    def test_resize_updates_dimensions(
        self, manager: SessionManager, dump_session: ScreenDumpSession
    ) -> None:
        session = manager.get("tool-test")
        # resize() on ScreenDumpSession updates rows/cols (tmux resize is best-effort)
        with patch("amplifier_module_tool_terminal_inspector.session_manager._run_tmux"):
            session.resize(24, 80)
        assert session.rows == 24
        assert session.cols == 80

    @pytest.mark.asyncio()
    async def test_close_removes_session(
        self, manager: SessionManager, dump_session: ScreenDumpSession
    ) -> None:
        with patch.object(dump_session, "close"):
            result = await manager.close("tool-test")
        assert result is True
        assert manager.get("tool-test") is None
