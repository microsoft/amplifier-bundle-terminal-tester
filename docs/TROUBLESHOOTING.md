# Terminal Inspector — Troubleshooting Guide

## Prerequisites Errors

### "tmux: command not found"

**Symptom:** Error when spawning in dump mode.
**Fix:** Install tmux.
```bash
# Ubuntu/Debian
sudo apt-get install tmux

# macOS
brew install tmux

# Arch
sudo pacman -S tmux
```

### "ModuleNotFoundError: No module named 'pyte'"

**Symptom:** Error when spawning in PTY mode.
**Fix:** Install pyte and Pillow.
```bash
pip install pyte Pillow
# or
uv pip install pyte Pillow
```

### "pyte is required for PTY mode"

**Symptom:** SessionManager raises RuntimeError on spawn with mode="pty".
**Fix:** Install pyte. Dump mode works without pyte — switch mode if the app supports the flags.

---

## App Launch Problems

### App does not appear / screen dump file never created

**Symptom:** `wait_for_dump()` times out; screen dump file at `--screen-dump-path` never appears.

**Possible causes and fixes:**
1. App does not support `--no-alt-screen` / `--screen-dump-path` flags → Use PTY mode instead
2. App crashed at startup → Check `amplifier doctor` or run the binary directly first
3. Incorrect binary path → Verify path exists: `ls -la <path>`
4. Missing config → Run `amplifier setup` to configure the provider

### "amplifier: Error: Environment variable X is not set"

**Symptom:** App exits immediately with environment variable error.
**Cause:** Usually test pollution writing bad values to `~/.amplifier/config.yaml`.
**Fix:**
```bash
# Check your config
cat ~/.amplifier/config.yaml

# Fix by restoring correct values:
# provider.primary.model should be "claude-sonnet-4-5" (not "gpt-4o")
# provider.primary.api_key_env should be "ANTHROPIC_API_KEY" (not "NEW_KEY")
```

### App takes very long to appear (> 20 seconds)

**Symptom:** TUI eventually appears but wait times out.
**Cause:** For the Amplifier TUI, the Python sidecar has a 10s startup timeout.
**Fix:** Increase `launch_wait` in spawn:
```python
terminal_inspector(operation="spawn",
    command="./amplifier --no-alt-screen --screen-dump-path /tmp/amp.txt",
    launch_wait=15.0)  # generous for sidecar startup
```
Then use `wait_for_text` instead of relying on the launch wait:
```python
terminal_inspector(operation="wait_for_text", session_id=sid,
    text="Enter send", timeout_s=20.0)
```

---

## Capture Problems

### Screen is blank (all empty rows)

**Symptom:** `screenshot()` returns text that is all empty.

**In dump mode:**
- The dump file may not have been created yet → use `wait_for_dump()` before first screenshot
- The app may be using alternate screen despite `--no-alt-screen` flag → check app startup

**In PTY mode:**
- App needs more time to render → increase `duration` in `pump_output()` or add a wait
- App may have written to `/dev/tty` directly, bypassing the PTY → use dump mode if the app supports it

### Screenshot shows stale content

**Symptom:** `screenshot()` always returns the same content regardless of interactions.

**In dump mode:** The dump file is not being updated.
- Verify the app is still running: check `alive` field in screenshot result
- Check if the session tmux window is still active: `tmux list-sessions`
- The app may have lost focus: `tmux send-keys -t <session>` requires the session to be active

**In PTY mode:** pyte stream is not receiving output.
- Call `pump_output()` explicitly before capture
- The app may write to `/dev/tty` instead of the PTY fd

### Frame number never advances (dump mode)

**Symptom:** `screenshot()["frame"]` stays at the same value even after interactions.

**Cause:** The app is not re-rendering after the keystroke.

**Diagnoses:**
1. Key not received → try a character key (e.g. `"x"`) to verify input is working
2. Key handled but no state change → check handler code
3. State changed but render not triggered → check if the event loop wakes up after background updates
4. App is in a blocking state (modal dialog, loading) that absorbs all input

---

## Keystroke Problems

### Keys not being received by the app

**Symptom:** Sending keys produces no screen change.

**In dump mode (tmux):**
- tmux session may be in a state that does not forward input
- Verify session exists: `tmux list-sessions | grep terminal-inspector-<id>`
- Try attaching: `tmux attach -t terminal-inspector-<id>` to inspect interactively

**In PTY mode:**
- PTY file descriptor may be closed → check if session is still alive
- App may be reading from `/dev/tty` instead of stdin

### Ctrl+, (Ctrl+comma) not working

**Symptom:** Sending `{CTRL+,}` or trying to open Settings panel does nothing.

**Cause:** `Ctrl+,` requires kitty keyboard protocol. Most terminals (xterm, VTE) cannot generate this key sequence.

**Workaround:** Use the command palette instead:
```python
terminal_inspector(operation="send_keys", session_id=sid, keys="{CTRL+K}")
terminal_inspector(operation="wait_for_text", session_id=sid, text="Command Palette", timeout_s=2)
terminal_inspector(operation="send_keys", session_id=sid, keys="settings{ENTER}")
```

### Tab key not cycling sidebar

**Symptom:** Tab is sent but sidebar state does not change.

**Possible causes:**
1. Command palette or workspace picker overlay is open and absorbing Tab → close overlay with Escape first
2. Input area has focus and Tab is moving cursor position → this would be a bug in the TUI
3. Frame not advancing after Tab → see "Frame number never advances"

---

## Session Management Problems

### "Session not found: <id>"

**Symptom:** Operations fail with session-not-found error after a working session.

**Causes:**
1. Session timed out (default: 30 minutes) → spawn a new session
2. Session closed explicitly elsewhere → check `list` operation
3. App crashed → `is_alive()` returns False, session should be cleaned up

### Session list shows stale/exited sessions

**Symptom:** `list` operation shows sessions that are no longer running.

**Fix:** Stale sessions are cleaned up automatically on the next `spawn()` or `list_sessions()` call. If they persist, call `close_all()` on the manager to clean up.

---

## Resize Problems

### Resize has no visible effect

**Symptom:** `resize()` operation succeeds but the app layout does not change.

**Possible causes:**
1. App does not handle SIGWINCH → capture to see if layout changed; some apps ignore it
2. App needs a redraw trigger → try `{CTRL+L}` after resize
3. pyte screen replaced but app did not re-render → pump output after resize

**In dump mode:** Resize uses `tmux resize-window` which sends SIGWINCH automatically.
**In PTY mode:** Resize sends TIOCSWINSZ ioctl + SIGWINCH explicitly.

### Layout looks wrong after resize (garbled)

**Symptom:** Boxes are misaligned, text overlaps, or elements are missing after resize.

**Cause:** Many TUI apps have minimum size requirements. Going below them produces undefined layout.

**Investigation:**
1. Resize back to original size to see if layout recovers
2. Test at the minimum size boundary: 80x24 is the traditional minimum

---

## PNG Screenshot Problems

### "No module named 'PIL'"

**Symptom:** PTY mode sessions produce `image_path: null` with no error, or error on screenshot.
**Fix:** `pip install Pillow`

### PNG screenshots are very small or use wrong font

**Symptom:** PNG is tiny or uses a bitmap fallback font.
**Cause:** No TrueType monospace font found at the standard paths.
**Fix:** Install a monospace font:
```bash
sudo apt-get install fonts-dejavu-core  # Ubuntu/Debian
```

### PNG screenshots have wrong colors

**Symptom:** Colors look wrong compared to what is visible in the terminal.
**Cause:** pyte's color model uses named + 256-color + true-color. Some color combinations may map differently.
**Note:** This is cosmetic only — the text content (`text` field) is accurate regardless of PNG color rendering.

---

## Amplifier TUI Specific Issues

### Status bar shows "working" after response completes

**Symptom:** After the LLM responds, the status bar still shows `— working`.
**Cause:** `SessionCompleted` event not clearing status (known bug in Phase 3).
**Evidence:** Row 1 of screenshot still contains "working" string after response.

### Session list empty after restart

**Symptom:** Sidebar Sessions tab shows "no sessions" despite prior conversations.
**Cause:** `refresh_session_list()` not called at startup (fixed in Phase 3 — verify you have the latest build).

### Provider error: 404 Not Found

**Symptom:** `error: Provider error: HTTP error: 404 Not Found` in conversation.
**Cause:** Config has wrong model name (e.g. `gpt-4o` with Anthropic provider).
**Fix:** Check `~/.amplifier/config.yaml`:
```yaml
provider:
  primary:
    name: anthropic
    model: claude-sonnet-4-5   # must be valid Anthropic model
    api_key_env: ANTHROPIC_API_KEY
```

### Provider error: 400 Bad Request

**Symptom:** `error: Provider error: HTTP error: 400 Bad Request`
**Cause:** Tool spec missing `"type": "object"` wrapper (fixed in Phase 3+ build).
**Fix:** Rebuild the TUI binary to get the fix.

### Double error prefix "error: error: message"

**Symptom:** Errors show as `error: error: actual message`.
**Cause:** Known rendering bug — display code adds "error: " prefix to events that already have it.

### Settings navigation stuck on Features tab

**Symptom:** `j`/`k` in Settings moves items within Features but cannot navigate to Providers/Routing/etc.
**Cause:** Known bug — `j`/`k` match arms fall through to default which moves the left nav.
**Workaround:** Use the command palette to reach specific settings sections.
