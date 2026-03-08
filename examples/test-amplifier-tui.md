# Example: Testing the Amplifier TUI

This example walks through a complete test session for the Amplifier TUI
(`bkrabach/superpowers-amplifier-tui`). It exercises the core flows:
launch, chat, sidebar, command palette, slash commands, and session persistence.

## Prerequisites

```bash
# Build the Amplifier TUI
cd ~/dev/tui
cargo build --release

# Verify doctor passes
./target/release/amplifier doctor

# Ensure ANTHROPIC_API_KEY is set
echo $ANTHROPIC_API_KEY
```

## Step 1: Launch in Screen-Dump Mode

The Amplifier TUI supports `--no-alt-screen` and `--screen-dump-path` for precise capture.

```python
result = terminal_inspector(
    operation="spawn",
    command="/home/bkrabach/dev/tui/target/release/amplifier "
            "--no-alt-screen --screen-dump-path /tmp/amp-screen.txt",
    mode="dump",
    cols=120,
    rows=40,
    launch_wait=5.0,   # short initial wait; we gate on wait_for_text
)
session_id = result["session_id"]
print(f"Session: {session_id}, mode: {result['mode']}")
```

## Step 2: Wait for Ready

The Amplifier TUI has a ~12-second startup due to the Python sidecar.
Gate on the key hints line rather than sleeping.

```python
ready = terminal_inspector(
    operation="wait_for_text",
    session_id=session_id,
    text="Enter send",
    timeout_s=20.0,
)
if not ready["found"]:
    snap = terminal_inspector(operation="screenshot", session_id=session_id)
    print("App did not reach ready state:")
    print(snap["text"])
    terminal_inspector(operation="close", session_id=session_id)
    raise RuntimeError("App not ready")

print(f"Ready in {ready['elapsed_s']:.1f}s")
```

## Step 3: Capture Initial State

```python
snap_initial = terminal_inspector(operation="screenshot", session_id=session_id)
print(f"Initial state (frame {snap_initial['frame']}):")
print(snap_initial["text"])

# Verify structure
text = snap_initial["text"]
assert "amplifier" in text, "Status bar should show 'amplifier'"
assert "Enter send" in text, "Key hints should be visible"
assert "↓ following" in text, "Following indicator should be visible"
```

Expected initial screen structure:
```
 amplifier                                    ← status bar (row 1)

                                              ← conversation area (rows 2-38, blank)

 ↓ following                                  ← separation bar (row 39)
──────────────────────────────────────────── ← input border (row 40)
>                                             ← input (row 41)
                                              ← padding (row 42)
Enter send  Tab sidebar  Ctrl+K cmd  ...      ← key hints (row 43)
```

## Step 4: Send a Message

```python
terminal_inspector(
    operation="send_text",
    session_id=session_id,
    text="Reply with exactly the word VERIFIED",
)
terminal_inspector(
    operation="send_keys",
    session_id=session_id,
    keys="{ENTER}",
)

# Wait for response (status bar shows "working" while streaming)
# The response completes when "VERIFIED" appears in the conversation
response_found = terminal_inspector(
    operation="wait_for_text",
    session_id=session_id,
    text="VERIFIED",
    timeout_s=30.0,
)
assert response_found["found"], "Expected 'VERIFIED' in response"
print(f"Response received in {response_found['elapsed_s']:.1f}s")

snap_after_chat = terminal_inspector(operation="screenshot", session_id=session_id)
print("After first message:")
print(snap_after_chat["text"])
```

## Step 5: Test Sidebar Cycling

The Tab key cycles through: Hidden → Agents → Sessions → Hidden.

```python
# Hidden → Agents
terminal_inspector(operation="send_keys", session_id=session_id, keys="{TAB}")
terminal_inspector(
    operation="wait_for_text",
    session_id=session_id,
    text="Agents",
    timeout_s=2.0,
)
snap_agents = terminal_inspector(operation="screenshot", session_id=session_id)
assert "Agents" in snap_agents["text"], "Agents sidebar should be visible"
print("✓ Agents sidebar opens on Tab")

# Agents → Sessions
terminal_inspector(operation="send_keys", session_id=session_id, keys="{TAB}")
terminal_inspector(
    operation="wait_for_text",
    session_id=session_id,
    text="Sessions",
    timeout_s=2.0,
)
snap_sessions = terminal_inspector(operation="screenshot", session_id=session_id)
assert "Sessions" in snap_sessions["text"], "Sessions sidebar should be visible"
print("✓ Sessions sidebar opens on Tab×2")

# Sessions → Hidden
terminal_inspector(operation="send_keys", session_id=session_id, keys="{TAB}")
# Sidebar hidden: Agents and Sessions headers should be gone
import time; time.sleep(0.3)
snap_hidden = terminal_inspector(operation="screenshot", session_id=session_id)
print("✓ Sidebar hidden on Tab×3")
```

## Step 6: Test Command Palette

```python
terminal_inspector(operation="send_keys", session_id=session_id, keys="{CTRL+K}")
terminal_inspector(
    operation="wait_for_text",
    session_id=session_id,
    text="Command Palette",
    timeout_s=2.0,
)
snap_palette = terminal_inspector(operation="screenshot", session_id=session_id)
assert "Command Palette" in snap_palette["text"], "Command palette should open"
print("✓ Command palette opens on Ctrl+K")

# Type in the palette
terminal_inspector(
    operation="send_keys",
    session_id=session_id,
    keys="clear",
)
import time; time.sleep(0.3)
snap_filtered = terminal_inspector(operation="screenshot", session_id=session_id)
print(f"Palette filtered to 'clear':")
# Should show /clear command in results

# Close palette
terminal_inspector(operation="send_keys", session_id=session_id, keys="{ESCAPE}")
print("✓ Palette closes on Escape")
```

## Step 7: Test /clear Slash Command

```python
terminal_inspector(
    operation="send_keys",
    session_id=session_id,
    keys="/clear{ENTER}",
)
import time; time.sleep(0.5)
snap_cleared = terminal_inspector(operation="screenshot", session_id=session_id)
# Conversation area should be empty after /clear
print("After /clear:")
print(snap_cleared["text"])
```

## Step 8: Test Shell Command

```python
terminal_inspector(
    operation="send_keys",
    session_id=session_id,
    keys="!echo terminal_tester_smoke_test{ENTER}",
)
shell_found = terminal_inspector(
    operation="wait_for_text",
    session_id=session_id,
    text="terminal_tester_smoke_test",
    timeout_s=5.0,
)
assert shell_found["found"], "Shell command output should appear in conversation"
print("✓ Shell command !echo works")
```

## Step 9: Clean Up

```python
terminal_inspector(operation="close", session_id=session_id)
print("Session closed.")
```

## Full Flow Summary

| Step | Test | Expected |
|------|------|----------|
| Launch | Spawn with dump flags | Session ID returned |
| Ready | wait_for_text "Enter send" | Found within 20s |
| Structure | Check status bar, key hints | "amplifier", "Enter send" visible |
| Chat | Send message, wait for response | "VERIFIED" in conversation |
| Sidebar | Tab×1, Tab×2, Tab×3 | Agents, Sessions, Hidden |
| Palette | Ctrl+K | "Command Palette" visible |
| /clear | /clear + Enter | Conversation area empty |
| Shell | !echo | Output in conversation |

## Notes

- **Startup time:** Expect 12–15 seconds for the Python sidecar. Always use
  `wait_for_text` with `timeout_s=20` rather than sleeping.

- **AI response time:** The `wait_for_text` for VERIFIED uses `timeout_s=30`.
  Increase for slow network conditions.

- **Session naming:** After the first message, the session name appears in
  the status bar (derived from the first user message).

- **Known issues:** Status bar may still show "working" after response
  completes (Phase 3 bug). Check the text content rather than status indicator
  to verify response completion.
