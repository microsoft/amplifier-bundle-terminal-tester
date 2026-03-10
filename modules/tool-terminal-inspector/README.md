# amplifier-module-tool-terminal-inspector

Terminal application testing tool for [Amplifier](https://github.com/microsoft/amplifier) — dual-mode capture via screen-dump (Ratatui) and PTY/pyte (universal).

## Overview

Provides the `terminal_inspector` tool that lets Amplifier agents launch, interact with, and inspect terminal applications (TUI and CLI). Supports two capture modes:

### Screen-Dump Mode (preferred for Ratatui/crossterm apps)

Apps that support `--no-alt-screen` and `--screen-dump-path` flags write their own render buffer to a file after every frame. The inspector reads that file directly — exact Ratatui buffer contents, no ANSI parsing, frame numbers for render-completion detection.

### PTY Mode (universal)

For any terminal app without modification. Forks a pseudo-terminal, runs `pyte` VT100 emulation, captures the virtual screen as text, ANSI color output, and PNG screenshots via Pillow.

Auto-detection: if the command contains `--screen-dump-path`, dump mode is used. Otherwise PTY mode.

## Operations

| Operation | Description |
|-----------|-------------|
| `spawn` | Launch a terminal app, returns `session_id` |
| `screenshot` | Capture current screen (text + optional PNG) |
| `send_keys` | Send keystrokes using `{KEY}` notation |
| `send_text` | Send plain text without `{KEY}` parsing |
| `find_text` | Search for text on screen, returns `[{row, col}]` |
| `wait_for_text` | Poll until text appears or timeout |
| `resize` | Resize the terminal (sends SIGWINCH) |
| `close` | Graceful shutdown (SIGTERM → 5s → SIGKILL) |
| `list` | List active sessions |

## Key Syntax

```
{ENTER} {TAB} {ESC} {UP} {DOWN} {LEFT} {RIGHT} {HOME} {END}
{PGUP} {PGDN} {F1}-{F12} {CTRL+A}-{CTRL+Z} {BACKSPACE} {DELETE} {SPACE}
```

Example: `"hello{ENTER}"`, `"{CTRL+K}"`, `"{UP}{UP}{ENTER}"`

## Typical Flow

```
spawn → wait_for_text (ready gate) → screenshot → send_keys → wait_for_text → screenshot → close
```

## Installation

```bash
pip install -e .
```

## Dependencies

- `pyte >= 0.8` — VT100 terminal emulator for PTY mode
- `Pillow >= 10.0` — PNG screenshot generation in PTY mode

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```
