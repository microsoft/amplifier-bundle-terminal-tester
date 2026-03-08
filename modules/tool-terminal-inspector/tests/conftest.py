"""Test configuration for tool-terminal-inspector tests.

Stubs out amplifier_core so tests run standalone without a full Amplifier
installation. Follows the same pattern as Diego Colombo's tui-tester.
"""

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock


def _stub_amplifier_core() -> None:
    """Inject a minimal amplifier_core stub into sys.modules."""
    if "amplifier_core" in sys.modules:
        return  # Real package installed — use it

    mock_core = ModuleType("amplifier_core")

    # Stub Tool base class
    class _StubTool:
        @property
        def name(self) -> str:
            return "stub"

        @property
        def description(self) -> str:
            return "stub"

        @property
        def input_schema(self) -> dict:
            return {"type": "object", "properties": {}}

        async def execute(self, input: dict) -> dict:
            return {"success": True}

    mock_core.Tool = _StubTool  # type: ignore[attr-defined]

    # Stub interfaces submodule
    mock_interfaces = ModuleType("amplifier_core.interfaces")
    mock_interfaces.Tool = _StubTool  # type: ignore[attr-defined]
    sys.modules["amplifier_core.interfaces"] = mock_interfaces

    # Stub models submodule
    mock_models = ModuleType("amplifier_core.models")

    class _StubToolResult:
        def __init__(self, success: bool = True, output: dict | None = None, error: dict | None = None):
            self.success = success
            self.output = output or {}
            self.error = error or {}

    mock_models.ToolResult = _StubToolResult  # type: ignore[attr-defined]
    sys.modules["amplifier_core.models"] = mock_models

    sys.modules["amplifier_core"] = mock_core


# Run stub injection immediately when conftest is loaded
_stub_amplifier_core()
