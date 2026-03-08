---
bundle:
  name: terminal-tester
  version: 1.0.0
  description: Terminal application testing and inspection using dual-mode capture (screen-dump + PTY/pyte)

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: terminal-tester:behaviors/terminal-tester

---

# Terminal Tester

Test, inspect, and debug TUI and CLI applications from within Amplifier sessions.

## Two Capture Modes

**Screen-dump mode** (preferred for Ratatui/crossterm apps):
Apps that support `--no-alt-screen` and `--screen-dump-path` flags write their own render buffer to a file after every frame. The inspector reads that file — pixel-perfect character content with frame numbers for synchronization. No ANSI parsing needed.

**PTY mode** (universal fallback):
For any terminal application. Forks a pseudo-terminal, emulates VT100 with pyte, captures the virtual screen buffer. Works with any app without modification. Provides text, ANSI color output, and PNG screenshots via Pillow.

Auto-detection: if the command includes `--screen-dump-path`, dump mode is used. Otherwise PTY mode.

@foundation:context/shared/common-system-base.md
