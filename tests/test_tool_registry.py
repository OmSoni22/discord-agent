"""Tests for ToolRegistry."""

import pytest
from app.tools.registry import ToolRegistry
from app.tools.calculator import CalculatorTool
from app.tools.file_reader import FileReaderTool


class TestToolRegistry:
    """Tests for the ToolRegistry class."""

    def test_register_tool(self, empty_registry):
        """Registering a tool makes it retrievable."""
        tool = CalculatorTool()
        empty_registry.register(tool)
        assert len(empty_registry.get_all()) == 1
        assert empty_registry.get_by_name("calculator") is tool

    def test_register_duplicate_raises(self, empty_registry):
        """Registering a tool with the same name raises ValueError."""
        empty_registry.register(CalculatorTool())
        with pytest.raises(ValueError, match="already registered"):
            empty_registry.register(CalculatorTool())

    def test_get_all_returns_list(self, tool_registry):
        """get_all returns all registered tools."""
        tools = tool_registry.get_all()
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert names == {"calculator", "file_reader"}

    def test_get_by_name_found(self, tool_registry):
        """get_by_name returns the tool if it exists."""
        tool = tool_registry.get_by_name("calculator")
        assert tool is not None
        assert tool.name == "calculator"

    def test_get_by_name_not_found(self, tool_registry):
        """get_by_name returns None for unknown tools."""
        assert tool_registry.get_by_name("nonexistent") is None

    def test_generate_specs_with_tools(self, tool_registry):
        """generate_specs produces formatted string with tool info."""
        specs = tool_registry.generate_specs()
        assert "calculator" in specs
        assert "file_reader" in specs
        assert "expression" in specs
        assert "file_path" in specs

    def test_generate_specs_empty(self, empty_registry):
        """generate_specs handles empty registry."""
        specs = empty_registry.generate_specs()
        assert specs == "No tools available."
