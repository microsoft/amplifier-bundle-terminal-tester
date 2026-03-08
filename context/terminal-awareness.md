# Terminal Testing (terminal-tester)

This bundle provides terminal application testing via dual-mode capture: screen-dump (for apps with explicit support) and PTY/pyte emulation (universal fallback).

## Available Agents

| Agent | Use For | Example Triggers |
|-------|---------|-----------------|
| `terminal-tester:terminal-operator` | Launch and interact with TUI/CLI apps, test keyboard navigation, verify screen output | "Test the TUI", "Launch amplifier and check the sidebar works", "Verify Ctrl+K opens the palette", "Run amplifier doctor and confirm all checks pass" |
| `terminal-tester:terminal-visual-tester` | Layout analysis at multiple sizes, responsive testing, before/after comparisons, visual regression | "Check how the layout looks at 80 columns", "Compare before and after this change visually", "Verify the sidebar renders correctly at all sizes" |
| `terminal-tester:terminal-debugger` | Rendering anomalies, frame-by-frame analysis, diagnosing why interactions don't work as expected | "Why doesn't the status bar clear after a response?", "The settings overlay is positioned wrong", "Debug why Tab isn't cycling the sidebar" |

## When to Use

Delegate to terminal-tester agents when you need to:
- Launch a TUI or CLI app and interact with it programmatically
- Verify that keystrokes produce expected screen changes
- Check layout, alignment, and rendering at different terminal sizes
- Debug visual issues that unit tests cannot catch
- Compare screen state before and after a code change
- Run automated interaction scripts against terminal applications

**Do not attempt terminal testing directly.** Always delegate to the specialist agents — they have the tool, the workflow discipline, and the troubleshooting knowledge.

## Two Capture Modes

**Screen-dump mode** (preferred, for Ratatui/crossterm apps):
- Launch with `--no-alt-screen --screen-dump-path /tmp/screen.txt`
- Reads exact Ratatui render buffer — no ANSI parsing, frame numbers for sync
- Fastest, most accurate for apps that support the flags

**PTY mode** (universal, for any terminal app):
- Forks a PTY, runs pyte VT100 emulation, captures screen buffer
- Works with Python TUIs (Textual, urwid), Go apps (Bubble Tea), anything
- Also generates PNG screenshots via Pillow for visual inspection

## Prerequisites

- `tmux` must be installed (used for screen-dump mode session management)
- `python3` with `pyte` and `Pillow` packages (for PTY mode screenshots)
- Target Ratatui apps: build with `--no-alt-screen` and `--screen-dump-path` flags for best results
