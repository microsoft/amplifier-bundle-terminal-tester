"""Key parsing utilities for terminal inspector tool.

Converts human-readable key notation like {ENTER}, {TAB}, {CTRL+C}
into terminal byte sequences (for PTY mode) or tmux key names (for dump mode).

Based on Diego Colombo's implementation in amplifier-bundle-tui-tester,
with additions for tmux key name mapping used in screen-dump mode.
"""

import re

# Special key mappings: {KEY} → terminal bytes (used in PTY mode)
SPECIAL_KEYS: dict[str, bytes] = {
    # Basic control keys
    "ENTER": b"\r",
    "RETURN": b"\r",
    "TAB": b"\t",
    "ESC": b"\x1b",
    "ESCAPE": b"\x1b",
    "BACKSPACE": b"\x7f",
    "DELETE": b"\x1b[3~",
    "SPACE": b" ",
    # Arrow keys
    "UP": b"\x1b[A",
    "DOWN": b"\x1b[B",
    "RIGHT": b"\x1b[C",
    "LEFT": b"\x1b[D",
    # Navigation keys
    "HOME": b"\x1b[H",
    "END": b"\x1b[F",
    "PGUP": b"\x1b[5~",
    "PAGEUP": b"\x1b[5~",
    "PGDN": b"\x1b[6~",
    "PAGEDOWN": b"\x1b[6~",
    "INSERT": b"\x1b[2~",
    # Function keys
    "F1": b"\x1bOP",
    "F2": b"\x1bOQ",
    "F3": b"\x1bOR",
    "F4": b"\x1bOS",
    "F5": b"\x1b[15~",
    "F6": b"\x1b[17~",
    "F7": b"\x1b[18~",
    "F8": b"\x1b[19~",
    "F9": b"\x1b[20~",
    "F10": b"\x1b[21~",
    "F11": b"\x1b[23~",
    "F12": b"\x1b[24~",
    # Control key combinations (full alphabet)
    "CTRL+A": b"\x01",
    "CTRL+B": b"\x02",
    "CTRL+C": b"\x03",
    "CTRL+D": b"\x04",
    "CTRL+E": b"\x05",
    "CTRL+F": b"\x06",
    "CTRL+G": b"\x07",
    "CTRL+H": b"\x08",
    "CTRL+I": b"\t",   # Same as TAB
    "CTRL+J": b"\n",
    "CTRL+K": b"\x0b",
    "CTRL+L": b"\x0c",
    "CTRL+M": b"\r",   # Same as ENTER
    "CTRL+N": b"\x0e",
    "CTRL+O": b"\x0f",
    "CTRL+P": b"\x10",
    "CTRL+Q": b"\x11",
    "CTRL+R": b"\x12",
    "CTRL+S": b"\x13",
    "CTRL+T": b"\x14",
    "CTRL+U": b"\x15",
    "CTRL+V": b"\x16",
    "CTRL+W": b"\x17",
    "CTRL+X": b"\x18",
    "CTRL+Y": b"\x19",
    "CTRL+Z": b"\x1a",
    "CTRL+[": b"\x1b",  # Same as ESC
    "CTRL+\\": b"\x1c",
    "CTRL+]": b"\x1d",
    "CTRL+^": b"\x1e",
    "CTRL+_": b"\x1f",
}

# tmux key name mappings: canonical key name → tmux send-keys argument
# Used in dump mode where we use tmux send-keys for input
TMUX_KEY_NAMES: dict[str, str] = {
    "ENTER": "Enter",
    "RETURN": "Enter",
    "TAB": "Tab",
    "ESC": "Escape",
    "ESCAPE": "Escape",
    "BACKSPACE": "BSpace",
    "DELETE": "Delete",
    "SPACE": "Space",
    "UP": "Up",
    "DOWN": "Down",
    "LEFT": "Left",
    "RIGHT": "Right",
    "HOME": "Home",
    "END": "End",
    "PGUP": "PPage",
    "PAGEUP": "PPage",
    "PGDN": "NPage",
    "PAGEDOWN": "NPage",
    "INSERT": "Insert",
    "F1": "F1",
    "F2": "F2",
    "F3": "F3",
    "F4": "F4",
    "F5": "F5",
    "F6": "F6",
    "F7": "F7",
    "F8": "F8",
    "F9": "F9",
    "F10": "F10",
    "F11": "F11",
    "F12": "F12",
    # Ctrl combinations → tmux C-<letter> notation
    "CTRL+A": "C-a",
    "CTRL+B": "C-b",
    "CTRL+C": "C-c",
    "CTRL+D": "C-d",
    "CTRL+E": "C-e",
    "CTRL+F": "C-f",
    "CTRL+G": "C-g",
    "CTRL+H": "C-h",
    "CTRL+I": "Tab",     # Same as TAB in tmux
    "CTRL+J": "C-j",
    "CTRL+K": "C-k",
    "CTRL+L": "C-l",
    "CTRL+M": "Enter",   # Same as ENTER in tmux
    "CTRL+N": "C-n",
    "CTRL+O": "C-o",
    "CTRL+P": "C-p",
    "CTRL+Q": "C-q",
    "CTRL+R": "C-r",
    "CTRL+S": "C-s",
    "CTRL+T": "C-t",
    "CTRL+U": "C-u",
    "CTRL+V": "C-v",
    "CTRL+W": "C-w",
    "CTRL+X": "C-x",
    "CTRL+Y": "C-y",
    "CTRL+Z": "C-z",
}

# Pattern to match {KEY} tokens
SPECIAL_KEY_PATTERN = re.compile(r"\{([^}]+)\}")


def parse_keys(input_string: str) -> bytes:
    """Parse a key string with {KEY} notation into terminal bytes (PTY mode).

    Args:
        input_string: String with optional {KEY} tokens, e.g. "hello{ENTER}"

    Returns:
        Bytes to write to the PTY master fd.

    Examples:
        >>> parse_keys("hello")
        b'hello'
        >>> parse_keys("{ENTER}")
        b'\\r'
        >>> parse_keys("test{TAB}more{ENTER}")
        b'test\\tmore\\r'
        >>> parse_keys("{UP}{UP}{ENTER}")
        b'\\x1b[A\\x1b[A\\r'
        >>> parse_keys("{CTRL+K}")
        b'\\x0b'
    """
    result = bytearray()
    pos = 0

    for match in SPECIAL_KEY_PATTERN.finditer(input_string):
        # Add any plain text before this {KEY} token
        if match.start() > pos:
            result.extend(input_string[pos : match.start()].encode("utf-8"))

        key_name = match.group(1).upper()
        if key_name in SPECIAL_KEYS:
            result.extend(SPECIAL_KEYS[key_name])
        else:
            # Unknown key — pass through as-is (don't silently drop it)
            result.extend(f"{{{match.group(1)}}}".encode())

        pos = match.end()

    # Any remaining plain text
    if pos < len(input_string):
        result.extend(input_string[pos:].encode("utf-8"))

    return bytes(result)


def parse_keys_for_tmux(input_string: str) -> list[str]:
    """Parse a key string into a list of tmux send-keys arguments (dump mode).

    Text segments are sent with -l (literal) flag; special keys are sent
    as named tmux keys. Returns a list of (is_literal, value) tuples.

    Args:
        input_string: String with optional {KEY} tokens

    Returns:
        List of (is_literal: bool, value: str) tuples.
        is_literal=True means: tmux send-keys -l <value>
        is_literal=False means: tmux send-keys <value>  (named key)

    Examples:
        >>> parse_keys_for_tmux("hello{ENTER}")
        [(True, 'hello'), (False, 'Enter')]
        >>> parse_keys_for_tmux("{CTRL+K}")
        [(False, 'C-k')]
        >>> parse_keys_for_tmux("Hi!")
        [(True, 'Hi!')]
    """
    segments: list[tuple[bool, str]] = []
    pos = 0
    pending_text = ""

    for match in SPECIAL_KEY_PATTERN.finditer(input_string):
        # Collect plain text before this token
        if match.start() > pos:
            pending_text += input_string[pos : match.start()]

        key_name = match.group(1).upper()
        tmux_name = TMUX_KEY_NAMES.get(key_name)

        if tmux_name is None:
            # Unknown key — treat as literal text
            pending_text += f"{{{match.group(1)}}}"
        else:
            # Flush pending text, then add the named key
            if pending_text:
                segments.append((True, pending_text))
                pending_text = ""
            segments.append((False, tmux_name))

        pos = match.end()

    # Any trailing plain text
    if pos < len(input_string):
        pending_text += input_string[pos:]
    if pending_text:
        segments.append((True, pending_text))

    return segments


def get_available_keys() -> list[str]:
    """Return sorted list of all recognized {KEY} names."""
    return sorted(SPECIAL_KEYS.keys())
