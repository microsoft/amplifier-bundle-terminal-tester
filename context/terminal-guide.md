# Terminal Inspector — Full Reference Guide

This guide is the complete reference for agents using the `terminal_inspector` tool to test and debug terminal applications. Read this before any testing session.

---

## Section 1: Two Capture Modes

### 1.1 Screen-Dump Mode (preferred for Ratatui/crossterm apps)

Apps built with Ratatui + crossterm can support two special flags:
- `--no-alt-screen` — renders to the primary screen buffer instead of the alternate screen
- `--screen-dump-path PATH` — after every `terminal.draw()` call, writes the Ratatui buffer to PATH

**How to use it:**
```
terminal_inspector(operation="spawn",
    command="./my-app --no-alt-screen --screen-dump-path /tmp/screen.txt",
    mode="dump",
    cols=120, rows=40)
```

**Dump file format:**
```
FRAME 42
SIZE 120x40
 my-app                    session-name     working
                                                    ← conversation rows
 ↓ following
────────────────────────────────────────────────
>
Enter send  Tab sidebar  Ctrl+K cmd  Ctrl+C quit
```

Line 1: `FRAME <N>` — frame counter increments on every render. Use to detect when the app has re-rendered after a keystroke.
Line 2: `SIZE <cols>x<rows>` — terminal dimensions.
Lines 3+: Each row of the terminal as plain text (trailing spaces stripped).

**Frame synchronization pattern:**
```python
before_frame = screenshot(session_id)["frame"]
send_keys(session_id, "{TAB}")
# Wait until frame increments (app has re-rendered)
wait_for_frame_change(session_id, before_frame, timeout_s=3.0)
after = screenshot(session_id)
```

**Advantages:** Exact Ratatui buffer contents, no ANSI parsing, frame numbers for sync, no alternate-screen capture issues.

### 1.2 PTY Mode (universal fallback)

Works with any terminal app — Textual, Bubble Tea, urwid, plain CLI tools. Forks a pseudo-terminal, runs pyte VT100 emulation.

**How to use it:**
```
terminal_inspector(operation="spawn",
    command="python -m my_textual_app",
    mode="pty",
    cols=120, rows=40)
```

**What you get from `screenshot`:**
- `text` — plain text, one line per row (trailing spaces stripped)
- `ansi` — ANSI-escaped text preserving colors/bold (for display)
- `image_path` — PNG screenshot rendered via Pillow

**Pump output:** After sending keys, the tool pumps the PTY for 0.5s to let async TUI frameworks finish rendering before capturing.

### 1.3 Auto-Detection

If the `mode` parameter is `"auto"` (default):
- If `command` contains `--screen-dump-path` → dump mode
- Otherwise → PTY mode

---

## Section 2: Tool Operations Reference

### `spawn` — Launch a terminal application

```python
result = terminal_inspector(
    operation="spawn",
    command="./amplifier --no-alt-screen --screen-dump-path /tmp/amp.txt",
    mode="auto",    # "auto" | "dump" | "pty"
    cols=120,       # terminal width (default: 120)
    rows=40,        # terminal height (default: 40)
)
session_id = result["session_id"]
```

Returns: `{session_id, mode, cols, rows, status, command}`

**Important:** Always wait after spawn. Use `wait_for_text` to gate on the app being ready rather than sleeping blindly.

### `screenshot` — Capture current screen state

```python
snap = terminal_inspector(
    operation="screenshot",
    session_id=session_id
)
# snap["text"]       — plain text content (numbered lines)
# snap["frame"]      — frame number (dump mode only; -1 in PTY mode)
# snap["rows"]       — terminal height
# snap["cols"]       — terminal width
# snap["image_path"] — PNG path (PTY mode only; None in dump mode)
# snap["alive"]      — bool: is process still running?
```

### `send_keys` — Send keystrokes using {KEY} syntax

```python
terminal_inspector(
    operation="send_keys",
    session_id=session_id,
    keys="Hello, world!{ENTER}",  # text + special keys mixed
    settle_s=0.2,  # seconds to wait after sending (default: 0.15)
)
```

Keys are parsed left-to-right. Plain characters are sent as UTF-8 bytes. `{KEY}` tokens are looked up in the special key table.

### `send_text` — Send plain text (no key parsing)

```python
terminal_inspector(
    operation="send_text",
    session_id=session_id,
    text="Hello, world!",  # sent literally, no {KEY} parsing
    settle_s=0.15,
)
```

Use this when you need to type text that contains `{` or `}` characters.

### `find_text` — Search for text on screen

```python
positions = terminal_inspector(
    operation="find_text",
    session_id=session_id,
    text="Enter send"
)
# Returns: [{row: 40, col: 1}, ...]  (1-based)
# Empty list if not found
```

### `wait_for_text` — Poll until text appears

```python
found = terminal_inspector(
    operation="wait_for_text",
    session_id=session_id,
    text="Enter send",
    timeout_s=15.0,   # max seconds to wait (default: 10.0)
    poll_s=0.2,       # poll interval (default: 0.2)
)
# Returns: {found: bool, elapsed_s: float, text: "..."}
```

Use this instead of `time.sleep()` to wait for app initialization or response completion.

### `resize` — Resize terminal (sends SIGWINCH)

```python
terminal_inspector(
    operation="resize",
    session_id=session_id,
    rows=24,
    cols=80
)
```

After resize, wait for a re-render before capturing: use `wait_for_text` or a short `settle_s`.

Some apps need `{CTRL+L}` after resize to force a full redraw.

### `close` — Graceful shutdown

```python
terminal_inspector(
    operation="close",
    session_id=session_id
)
# Sends SIGTERM, waits 5s, then SIGKILL
# Also cleans up dump file and tmux session
```

Always close sessions when done, including on error paths.

### `list` — List active sessions

```python
sessions = terminal_inspector(operation="list")
# Returns: {sessions: [{session_id, command, mode, status, rows, cols, created_at}], count: N}
```

---

## Section 3: Key Syntax Reference

Use `{KEY}` notation inside `send_keys`. Keys are case-insensitive.

### Basic Control Keys
| Syntax | Description | Terminal Bytes |
|--------|-------------|----------------|
| `{ENTER}` or `{RETURN}` | Enter/Return | `\r` |
| `{TAB}` | Tab | `\t` |
| `{ESC}` or `{ESCAPE}` | Escape | `\x1b` |
| `{BACKSPACE}` | Backspace | `\x7f` |
| `{DELETE}` | Delete | `\x1b[3~` |
| `{SPACE}` | Space | ` ` |

### Arrow Keys
| Syntax | Description |
|--------|-------------|
| `{UP}` | Arrow up |
| `{DOWN}` | Arrow down |
| `{LEFT}` | Arrow left |
| `{RIGHT}` | Arrow right |

### Navigation Keys
| Syntax | Description |
|--------|-------------|
| `{HOME}` | Home |
| `{END}` | End |
| `{PGUP}` or `{PAGEUP}` | Page up |
| `{PGDN}` or `{PAGEDOWN}` | Page down |
| `{INSERT}` | Insert |

### Function Keys
`{F1}` through `{F12}`

### Ctrl Combinations
`{CTRL+A}` through `{CTRL+Z}` — full alphabet supported.
Aliases: `{CTRL+I}` = Tab, `{CTRL+M}` = Enter, `{CTRL+[}` = Escape.

### Mixed Examples
```
"Hello, world!{ENTER}"           → type text then press Enter
"/clear{ENTER}"                  → slash command
"{CTRL+K}"                       → open command palette
"{TAB}{TAB}"                     → press Tab twice
"item name{TAB}description{ENTER}" → fill form
"{UP}{UP}{DOWN}{ENTER}"          → navigate list then select
```

---

## Section 4: Timing and Synchronization

### The Golden Rule: Don't Use Fixed Delays

Bad pattern (brittle):
```python
send_keys(session_id, "{TAB}")
time.sleep(2)  # ← arbitrary, slow, and still may fail
screenshot(session_id)
```

Good pattern (reliable):
```python
send_keys(session_id, "{TAB}")
wait_for_text(session_id, "Agents", timeout_s=3.0)  # wait for sidebar header
screenshot(session_id)
```

### Launch Wait

After `spawn`, use `wait_for_text` to wait for the app's ready indicator:

```python
result = terminal_inspector(operation="spawn", command="...")
sid = result["session_id"]
terminal_inspector(operation="wait_for_text", session_id=sid,
    text="Enter send",  # key hints appear when TUI is fully ready
    timeout_s=20.0)     # generous timeout for slow-starting apps
snap = terminal_inspector(operation="screenshot", session_id=sid)
```

For the Amplifier TUI specifically: the sidecar has a ~10s startup, so use `timeout_s=15`.

### Frame Detection (Screen-Dump Mode)

```python
before_frame = terminal_inspector(operation="screenshot", session_id=sid)["frame"]
terminal_inspector(operation="send_keys", session_id=sid, keys="/clear{ENTER}")
# Poll until frame increments
for _ in range(30):  # up to 3s
    time.sleep(0.1)
    snap = terminal_inspector(operation="screenshot", session_id=sid)
    if snap["frame"] > before_frame:
        break  # app has re-rendered
```

### After Resize

```python
terminal_inspector(operation="resize", session_id=sid, rows=24, cols=80)
# Most apps re-render on SIGWINCH — gate on content rather than sleeping
terminal_inspector(operation="wait_for_text", session_id=sid,
    text=">",  # input prompt should still be present after resize
    timeout_s=3.0)
snap = terminal_inspector(operation="screenshot", session_id=sid)
```

---

## Section 5: Common Test Patterns

### Pattern 1: Basic Interaction Test
```python
# 1. Spawn and wait for ready
result = terminal_inspector(operation="spawn",
    command="./app --no-alt-screen --screen-dump-path /tmp/app.txt",
    mode="dump", cols=120, rows=40)
sid = result["session_id"]
terminal_inspector(operation="wait_for_text", session_id=sid,
    text="ready_indicator", timeout_s=15.0)

# 2. Capture initial state — verify structure
snap1 = terminal_inspector(operation="screenshot", session_id=sid)

# 3. Interact
terminal_inspector(operation="send_keys", session_id=sid, keys="Hello!{ENTER}")

# 4. Wait for response then verify
terminal_inspector(operation="wait_for_text", session_id=sid,
    text="> Hello!", timeout_s=5.0)
snap2 = terminal_inspector(operation="screenshot", session_id=sid)

# 5. Clean up
terminal_inspector(operation="close", session_id=sid)
```

### Pattern 2: Responsive Layout Testing
```python
result = terminal_inspector(operation="spawn", command="...", cols=200, rows=50)
sid = result["session_id"]
terminal_inspector(operation="wait_for_text", session_id=sid, text="Enter send", timeout_s=15)

captures = {}
for cols, label in [(200, "wide"), (120, "standard"), (80, "narrow"), (60, "minimum")]:
    terminal_inspector(operation="resize", session_id=sid, rows=40, cols=cols)
    terminal_inspector(operation="wait_for_text", session_id=sid, text=">", timeout_s=3)
    captures[label] = terminal_inspector(operation="screenshot", session_id=sid)

terminal_inspector(operation="close", session_id=sid)
# Analyze: does layout adapt correctly at each size?
```

### Pattern 3: Feature Verification
```python
# Verify a specific feature works end-to-end
result = terminal_inspector(operation="spawn", command="...", ...)
sid = result["session_id"]
terminal_inspector(operation="wait_for_text", session_id=sid, text="Enter send", timeout_s=15)

# Test Tab cycles sidebar states
for expected in ["Agents", "Sessions", "Enter send"]:
    before = terminal_inspector(operation="screenshot", session_id=sid)["frame"]
    terminal_inspector(operation="send_keys", session_id=sid, keys="{TAB}")
    terminal_inspector(operation="wait_for_text", session_id=sid, text=expected, timeout_s=2)
    snap = terminal_inspector(operation="screenshot", session_id=sid)
    # Verify expected text is visible

terminal_inspector(operation="close", session_id=sid)
```

### Pattern 4: Before/After Comparison
```python
# Capture before a change, apply change, capture after
snap_before = terminal_inspector(operation="screenshot", session_id=sid)

# Make the change (slash command, key press, etc.)
terminal_inspector(operation="send_keys", session_id=sid, keys="/clear{ENTER}")
terminal_inspector(operation="wait_for_text", session_id=sid, text="Enter send", timeout_s=3)

snap_after = terminal_inspector(operation="screenshot", session_id=sid)

# Compare: what changed between snap_before and snap_after?
```

---

## Section 6: Visual Analysis Checklist

When analyzing a screenshot, work through this checklist:

### Layout & Structure
- [ ] All UI zones visible: status bar, conversation area, separation bar, input, key hints
- [ ] Zones correctly proportioned — no zone oversized or missing
- [ ] No content truncation at edges
- [ ] Box-drawing characters intact (borders, separators)
- [ ] Sidebar (if open): proper border, content visible

### Text & Content
- [ ] Status bar shows correct info (app name, session, state)
- [ ] Key hints correct and complete
- [ ] Conversation content readable, not overlapping
- [ ] Error messages use correct prefix format
- [ ] Input prompt visible (typically `>`)

### Interactive State
- [ ] Cursor position correct (inside input area)
- [ ] Selected/active items visually distinct
- [ ] Overlays (if open): properly centered, Clear border, content visible
- [ ] Following indicator matches scroll state

### Responsive Behavior (resize tests)
- [ ] All critical elements still visible after resize
- [ ] No elements overlap at smaller sizes
- [ ] Sidebar auto-hides at narrow widths (expected behavior)
- [ ] Input area always accessible

### Common Issues to Detect
- Status bar shows "working" after response completed (stuck state)
- Overlay not dismissed after Escape
- Sidebar shows "no agents yet" despite agents being active
- Session list empty despite prior sessions existing
- Double prefix on errors ("error: error: ...")
- Whitespace-only input sent to provider

---

## Section 7: Amplifier TUI Specific Reference

### Launch Command
```
./target/release/amplifier --no-alt-screen --screen-dump-path /tmp/amp-screen.txt
```

Use mode="dump" — the TUI supports the flags.

**Startup time:** ~12–15 seconds. The Python sidecar has a 10s startup timeout.
Use: `wait_for_text(session_id, "Enter send", timeout_s=20)`

### Expected Initial Screen Structure
```
Row 1:  " amplifier — <workspace> — <session>"   ← status bar
Rows 2–38: conversation area (blank initially)
Row 39: " ↓ following"                           ← separation bar  
Row 40: "─────────────────────────"              ← input border
Row 41: ">"                                      ← input line
Row 42: ""                                       ← input padding
Row 43: "Enter send  Tab sidebar  Ctrl+K cmd..." ← key hints
```

### Key Bindings Reference
| Key | Action |
|-----|--------|
| `Enter` | Send message |
| `Tab` | Cycle sidebar (Hidden → Agents → Sessions → Hidden) |
| `Ctrl+K` | Command palette |
| `Ctrl+W` | Workspace picker |
| `Ctrl+,` | Settings panel (requires kitty keyboard protocol) |
| `Ctrl+C` | Quit |
| `{UP}/{DOWN}` | Scroll conversation |
| `/clear` + Enter | Clear conversation |
| `/new` + Enter | New session |
| `/quit` + Enter | Quit |
| `/model <name>` + Enter | Switch model |
| `!<cmd>` + Enter | Shell command |

### Sidebar States
After Tab presses:
1. Hidden (default) — no sidebar column
2. Agents — left panel shows "Agents" header + agent list
3. Sessions — left panel shows "Sessions" header + session list
4. Hidden (wraps around)

### Settings Panel (Ctrl+,)
Navigate with `j`/`k` (items within section) and arrow keys (section nav).
Sections: Features, Providers, Routing, Profiles, Catalog, Advanced.

**Known issue:** `Ctrl+,` requires kitty keyboard protocol. Most terminals cannot send this key. Use the command palette (`Ctrl+K` → search "settings") as the alternative.
