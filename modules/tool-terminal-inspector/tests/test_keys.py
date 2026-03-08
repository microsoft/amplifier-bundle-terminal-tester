"""Tests for keys.py — key parser for terminal inspector tool."""

import pytest

from amplifier_module_tool_terminal_inspector.keys import (
    get_available_keys,
    parse_keys,
    parse_keys_for_tmux,
)


class TestParseKeys:
    """Tests for parse_keys() — converts {KEY} notation to PTY bytes."""

    def test_plain_text_passthrough(self) -> None:
        assert parse_keys("hello") == b"hello"

    def test_empty_string(self) -> None:
        assert parse_keys("") == b""

    def test_single_enter(self) -> None:
        assert parse_keys("{ENTER}") == b"\r"

    def test_return_alias(self) -> None:
        assert parse_keys("{RETURN}") == b"\r"

    def test_tab(self) -> None:
        assert parse_keys("{TAB}") == b"\t"

    def test_esc(self) -> None:
        assert parse_keys("{ESC}") == b"\x1b"

    def test_escape_alias(self) -> None:
        assert parse_keys("{ESCAPE}") == b"\x1b"

    def test_backspace(self) -> None:
        assert parse_keys("{BACKSPACE}") == b"\x7f"

    def test_delete(self) -> None:
        assert parse_keys("{DELETE}") == b"\x1b[3~"

    def test_space(self) -> None:
        assert parse_keys("{SPACE}") == b" "

    def test_arrow_up(self) -> None:
        assert parse_keys("{UP}") == b"\x1b[A"

    def test_arrow_down(self) -> None:
        assert parse_keys("{DOWN}") == b"\x1b[B"

    def test_arrow_right(self) -> None:
        assert parse_keys("{RIGHT}") == b"\x1b[C"

    def test_arrow_left(self) -> None:
        assert parse_keys("{LEFT}") == b"\x1b[D"

    def test_home(self) -> None:
        assert parse_keys("{HOME}") == b"\x1b[H"

    def test_end(self) -> None:
        assert parse_keys("{END}") == b"\x1b[F"

    def test_page_up(self) -> None:
        assert parse_keys("{PGUP}") == b"\x1b[5~"

    def test_page_up_alias(self) -> None:
        assert parse_keys("{PAGEUP}") == b"\x1b[5~"

    def test_page_down(self) -> None:
        assert parse_keys("{PGDN}") == b"\x1b[6~"

    def test_page_down_alias(self) -> None:
        assert parse_keys("{PAGEDOWN}") == b"\x1b[6~"

    def test_insert(self) -> None:
        assert parse_keys("{INSERT}") == b"\x1b[2~"

    def test_f1(self) -> None:
        assert parse_keys("{F1}") == b"\x1bOP"

    def test_f2(self) -> None:
        assert parse_keys("{F2}") == b"\x1bOQ"

    def test_f3(self) -> None:
        assert parse_keys("{F3}") == b"\x1bOR"

    def test_f4(self) -> None:
        assert parse_keys("{F4}") == b"\x1bOS"

    def test_f5(self) -> None:
        assert parse_keys("{F5}") == b"\x1b[15~"

    def test_f12(self) -> None:
        assert parse_keys("{F12}") == b"\x1b[24~"

    def test_ctrl_a(self) -> None:
        assert parse_keys("{CTRL+A}") == b"\x01"

    def test_ctrl_c(self) -> None:
        assert parse_keys("{CTRL+C}") == b"\x03"

    def test_ctrl_k(self) -> None:
        assert parse_keys("{CTRL+K}") == b"\x0b"

    def test_ctrl_w(self) -> None:
        assert parse_keys("{CTRL+W}") == b"\x17"

    def test_ctrl_z(self) -> None:
        assert parse_keys("{CTRL+Z}") == b"\x1a"

    def test_ctrl_i_is_tab(self) -> None:
        assert parse_keys("{CTRL+I}") == parse_keys("{TAB}")

    def test_ctrl_m_is_enter(self) -> None:
        assert parse_keys("{CTRL+M}") == parse_keys("{ENTER}")

    def test_mixed_text_and_key(self) -> None:
        assert parse_keys("hello{ENTER}") == b"hello\r"

    def test_key_then_text(self) -> None:
        assert parse_keys("{TAB}world") == b"\tworld"

    def test_text_key_text(self) -> None:
        assert parse_keys("foo{TAB}bar") == b"foo\tbar"

    def test_consecutive_keys(self) -> None:
        assert parse_keys("{UP}{UP}{DOWN}{ENTER}") == b"\x1b[A\x1b[A\x1b[B\r"

    def test_slash_command(self) -> None:
        assert parse_keys("/clear{ENTER}") == b"/clear\r"

    def test_case_insensitive(self) -> None:
        assert parse_keys("{enter}") == parse_keys("{ENTER}")
        assert parse_keys("{tab}") == parse_keys("{TAB}")
        assert parse_keys("{ctrl+k}") == parse_keys("{CTRL+K}")

    def test_unknown_key_passes_through(self) -> None:
        # Unknown {KEY} tokens are passed through as-is (not silently dropped)
        result = parse_keys("{UNKNOWN_KEY}")
        assert b"UNKNOWN_KEY" in result

    def test_unicode_text(self) -> None:
        result = parse_keys("Hello 世界{ENTER}")
        assert "世界".encode() in result
        assert result.endswith(b"\r")

    def test_ctrl_full_alphabet(self) -> None:
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            result = parse_keys(f"{{CTRL+{letter}}}")
            assert len(result) == 1  # all ctrl+letter combos are single bytes


class TestParseKeysForTmux:
    """Tests for parse_keys_for_tmux() — converts {KEY} notation to tmux segments."""

    def test_plain_text(self) -> None:
        segments = parse_keys_for_tmux("hello")
        assert segments == [(True, "hello")]

    def test_single_enter(self) -> None:
        segments = parse_keys_for_tmux("{ENTER}")
        assert segments == [(False, "Enter")]

    def test_tab(self) -> None:
        segments = parse_keys_for_tmux("{TAB}")
        assert segments == [(False, "Tab")]

    def test_ctrl_k(self) -> None:
        segments = parse_keys_for_tmux("{CTRL+K}")
        assert segments == [(False, "C-k")]

    def test_ctrl_w(self) -> None:
        segments = parse_keys_for_tmux("{CTRL+W}")
        assert segments == [(False, "C-w")]

    def test_esc(self) -> None:
        segments = parse_keys_for_tmux("{ESC}")
        assert segments == [(False, "Escape")]

    def test_mixed_text_and_key(self) -> None:
        segments = parse_keys_for_tmux("hello{ENTER}")
        assert segments == [(True, "hello"), (False, "Enter")]

    def test_slash_command(self) -> None:
        segments = parse_keys_for_tmux("/clear{ENTER}")
        assert segments == [(True, "/clear"), (False, "Enter")]

    def test_multiple_keys(self) -> None:
        segments = parse_keys_for_tmux("{TAB}{TAB}")
        assert segments == [(False, "Tab"), (False, "Tab")]

    def test_text_key_text(self) -> None:
        segments = parse_keys_for_tmux("foo{TAB}bar")
        assert segments == [(True, "foo"), (False, "Tab"), (True, "bar")]

    def test_empty_string(self) -> None:
        assert parse_keys_for_tmux("") == []

    def test_up_arrow(self) -> None:
        segments = parse_keys_for_tmux("{UP}")
        assert segments == [(False, "Up")]

    def test_page_up(self) -> None:
        segments = parse_keys_for_tmux("{PGUP}")
        assert segments == [(False, "PPage")]

    def test_unknown_key_treated_as_literal(self) -> None:
        # Unknown {KEY} tokens should be passed through as literal text
        segments = parse_keys_for_tmux("{UNKNOWN_KEY}")
        assert len(segments) == 1
        is_literal, value = segments[0]
        assert is_literal is True
        assert "UNKNOWN_KEY" in value

    def test_case_insensitive(self) -> None:
        assert parse_keys_for_tmux("{enter}") == parse_keys_for_tmux("{ENTER}")

    def test_ctrl_i_maps_to_tab(self) -> None:
        segments = parse_keys_for_tmux("{CTRL+I}")
        assert segments == [(False, "Tab")]

    def test_ctrl_m_maps_to_enter(self) -> None:
        segments = parse_keys_for_tmux("{CTRL+M}")
        assert segments == [(False, "Enter")]


class TestGetAvailableKeys:
    """Tests for get_available_keys()."""

    def test_returns_sorted_list(self) -> None:
        keys = get_available_keys()
        assert isinstance(keys, list)
        assert keys == sorted(keys)

    def test_contains_enter(self) -> None:
        assert "ENTER" in get_available_keys()

    def test_contains_all_ctrl_letters(self) -> None:
        keys = get_available_keys()
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            assert f"CTRL+{letter}" in keys

    def test_contains_arrows(self) -> None:
        keys = get_available_keys()
        for arrow in ["UP", "DOWN", "LEFT", "RIGHT"]:
            assert arrow in keys

    def test_contains_function_keys(self) -> None:
        keys = get_available_keys()
        for n in range(1, 13):
            assert f"F{n}" in keys
