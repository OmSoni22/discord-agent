"""Tests for ToolRegistry."""

import pytest
from app.tools.registry import ToolRegistry
from app.tools.web_search_tool import WebSearchTool
from app.tools.notion_tool import NotionTool


class TestToolRegistry:
    """Tests for the ToolRegistry class."""

    def test_register_tool(self, empty_registry):
        """Registering a tool makes it retrievable."""
        tool = WebSearchTool()
        empty_registry.register(tool)
        assert len(empty_registry.get_all()) == 1
        assert empty_registry.get_by_name("web_search") is tool

    def test_register_duplicate_raises(self, empty_registry):
        """Registering a tool with the same name raises ValueError."""
        empty_registry.register(WebSearchTool())
        with pytest.raises(ValueError, match="already registered"):
            empty_registry.register(WebSearchTool())

    def test_get_all_returns_list(self, tool_registry):
        """get_all returns all registered tools."""
        tools = tool_registry.get_all()
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert names == {"web_search", "notion"}

    def test_get_by_name_found(self, tool_registry):
        """get_by_name returns the tool if it exists."""
        tool = tool_registry.get_by_name("web_search")
        assert tool is not None
        assert tool.name == "web_search"

    def test_get_by_name_not_found(self, tool_registry):
        """get_by_name returns None for unknown tools."""
        assert tool_registry.get_by_name("nonexistent") is None

    def test_generate_specs_with_tools(self, tool_registry):
        """generate_specs produces formatted string with tool info."""
        specs = tool_registry.generate_specs()
        assert "web_search" in specs
        assert "notion" in specs
        assert "query" in specs
        assert "action" in specs

    def test_generate_specs_empty(self, empty_registry):
        """generate_specs handles empty registry."""
        specs = empty_registry.generate_specs()
        assert specs == "No tools available."
