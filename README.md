# amplifier-bundle-terminal-tester

Test, inspect, and debug TUI and CLI applications from within Amplifier sessions.

Combines the best of two capture approaches into a single bundle with three specialist agents and a production-quality Python tool module.

## Two Capture Modes

### Screen-Dump Mode (preferred for Ratatui/crossterm apps)

Apps that support `--no-alt-screen` and `--screen-dump-path` flags write their own render buffer to a file after every frame. The inspector reads that file directly — exact Ratatui buffer contents, no ANSI parsing, frame numbers for synchronization.

```bash
# The Amplifier TUI supports these flags:
./amplifier --no-alt-screen --screen-dump-path /tmp/screen.txt
```

**Why it is better for compatible apps:**
- Pixel-perfect: reads Ratatui's own internal buffer, not a terminal emulator approximation
- Frame numbers: detect render completion precisely (`frame > before_frame`)
- No alternate screen capture issues: the dump file is a plain text file
- No ANSI parsing: pure character content

### PTY Mode (universal)

For any terminal app without modification. Forks a pseudo-terminal, runs pyte VT100 emulation, captures the virtual screen as text, ANSI color output, and PNG screenshots via Pillow.

Based on Diego Colombo's [`amplifier-bundle-tui-tester`](https://github.com/colombod/amplifier-bundle-tui-tester) with enhancements for integration with the screen-dump approach.

```python
terminal_inspector(operation="spawn", command="python -m my_textual_app", mode="pty")
```

## Quick Start

### Installation

**Add as an app bundle (recommended):**
```bash
amplifier bundle add git+https://github.com/microsoft/amplifier-bundle-terminal-tester@main#subdirectory=behaviors/terminal-tester.yaml --app
```

**Compose into another bundle:**
```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-bundle-terminal-tester@main#subdirectory=behaviors/terminal-tester.yaml
    as: terminal-tester
```

### Prerequisites
- `tmux` (for screen-dump mode)
- `python3` with `pyte` and `Pillow` (for PTY mode and screenshots):
  ```bash
  pip install pyte Pillow
  ```

### Basic Usage

```python
# Launch the Amplifier TUI in screen-dump mode
result = terminal_inspector(
    operation="spawn",
    command="./amplifier --no-alt-screen --screen-dump-path /tmp/amp.txt",
    mode="dump",
    cols=120,
    rows=40,
)
sid = result["session_id"]

# Wait for ready (use wait_for_text, not time.sleep)
terminal_inspector(operation="wait_for_text", session_id=sid,
    text="Enter send", timeout_s=20.0)

# Capture initial state
snap = terminal_inspector(operation="screenshot", session_id=sid)
print(snap["text"])

# Interact
terminal_inspector(operation="send_keys", session_id=sid, keys="Hello!{ENTER}")

# Wait for response
terminal_inspector(operation="wait_for_text", session_id=sid,
    text="Hello!", timeout_s=30.0)

# Clean up
terminal_inspector(operation="close", session_id=sid)
```

## Agents

### `terminal-operator` (primary)

Drives terminal applications — launches them, interacts via keyboard, captures screen state, and verifies results. Systematic six-step workflow with 3-attempt failure budget.

Use for: keyboard navigation testing, feature verification, CLI command output checks, automated interaction flows.

### `terminal-visual-tester`

Visual quality analysis at multiple sizes. Captures screen state at standard breakpoints (60, 80, 100, 120, 160, 200 columns), applies full visual checklist, reports defects with severity ratings.

Use for: responsive layout testing, before/after comparison, visual regression, accessibility review.

### `terminal-debugger`

Deep investigator for rendering anomalies. Frame-by-frame analysis, keystroke-response verification, root cause identification for "it looks wrong but I can't figure out why" problems.

Use for: stuck status indicators, non-responsive keys, overlay positioning issues, rendering pipeline bugs.

## Tool Operations Reference

| Operation | Description | Required Params |
|-----------|-------------|----------------|
| `spawn` | Launch terminal app | `command` |
| `screenshot` | Capture current screen | `session_id` |
| `send_keys` | Send keystrokes with `{KEY}` notation | `session_id`, `keys` |
| `send_text` | Send plain text (no key parsing) | `session_id`, `text` |
| `find_text` | Search for text, returns positions | `session_id`, `text` |
| `wait_for_text` | Poll until text appears | `session_id`, `text` |
| `resize` | Resize terminal (sends SIGWINCH) | `session_id` |
| `close` | Graceful shutdown (SIGTERM → 5s → SIGKILL) | `session_id` |
| `list` | List active sessions | — |

## Key Syntax

Use `{KEY}` notation in `send_keys`:

```
{ENTER} {TAB} {ESC} {BACKSPACE} {DELETE} {SPACE}
{UP} {DOWN} {LEFT} {RIGHT}
{HOME} {END} {PGUP} {PGDN} {INSERT}
{F1} - {F12}
{CTRL+A} - {CTRL+Z}
```

Mixed example: `"Hello, world!{ENTER}"`, `"{CTRL+K}"`, `"{UP}{UP}{DOWN}{ENTER}"`

## Key Design Decisions

### Why not just use tmux capture-pane?

`tmux capture-pane` reads the primary screen buffer. Ratatui uses the **alternate screen buffer** (`EnterAlternateScreen`), which is not captured by `capture-pane` in detached sessions. Additionally, crossterm opens `/dev/tty` directly for raw-mode I/O, bypassing the PTY master fd that pexpect and similar tools read.

The screen-dump approach works because it reads Ratatui's own internal buffer *after* the draw call — no terminal emulation needed.

### Why support PTY mode too?

Not all apps can be modified to add `--screen-dump-path`. PTY + pyte works universally for Python TUIs (Textual, urwid), Go apps (Bubble Tea), and any other terminal application.

### Naming: terminal-tester vs tui-tester

Diego Colombo's excellent [`amplifier-bundle-tui-tester`](https://github.com/colombod/amplifier-bundle-tui-tester) covers PTY-based TUI testing. This bundle uses `terminal-tester` to:
1. Avoid namespace collision with his bundle
2. Reflect the broader scope (CLI tools, not just TUI apps)
3. Incorporate the screen-dump approach specific to Ratatui

## Credits

- **PTY + pyte approach**: Diego Colombo ([amplifier-bundle-tui-tester](https://github.com/colombod/amplifier-bundle-tui-tester))
- **Screen-dump approach**: Developed during amplifier-tui Phase 6
- **Bundle structure**: Inspired by [amplifier-bundle-browser-tester](https://github.com/microsoft/amplifier-bundle-browser-tester)

## License

MIT
