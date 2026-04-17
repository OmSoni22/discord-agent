"""Tests for built-in tools (Calculator, FileReader, WebSearch, Notion)."""

import os
import pytest
from unittest.mock import patch, MagicMock
from app.tools.calculator import CalculatorTool
from app.tools.file_reader import FileReaderTool


class TestCalculatorTool:
    """Tests for the CalculatorTool."""

    def setup_method(self):
        self.tool = CalculatorTool()

    def test_basic_addition(self):
        assert self.tool._run("2 + 3") == "5"

    def test_multiplication(self):
        assert self.tool._run("6 * 7") == "42"

    def test_division(self):
        assert self.tool._run("10 / 4") == "2.5"

    def test_power(self):
        assert self.tool._run("2 ** 10") == "1024"

    def test_sqrt(self):
        assert self.tool._run("sqrt(16)") == "4.0"

    def test_pi(self):
        result = float(self.tool._run("pi"))
        assert abs(result - 3.14159265) < 0.001

    def test_complex_expression(self):
        result = float(self.tool._run("sqrt(9) + 2 * 3"))
        assert result == 9.0

    def test_invalid_expression(self):
        result = self.tool._run("invalid_expr")
        assert "Error" in result

    def test_division_by_zero(self):
        result = self.tool._run("1 / 0")
        assert "Error" in result


class TestFileReaderTool:
    """Tests for the FileReaderTool."""

    TEMP_DIR = os.path.join(os.path.dirname(__file__), "_tmp_test")

    def setup_method(self):
        self.tool = FileReaderTool()
        os.makedirs(self.TEMP_DIR, exist_ok=True)

    def teardown_method(self):
        import shutil
        if os.path.exists(self.TEMP_DIR):
            shutil.rmtree(self.TEMP_DIR, ignore_errors=True)

    def test_read_existing_file(self):
        """Read a real file and get its contents."""
        file_path = os.path.join(self.TEMP_DIR, "test.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("hello world")
        result = self.tool._run(file_path)
        assert result == "hello world"

    def test_file_not_found(self):
        result = self.tool._run("/nonexistent/path/file.txt")
        assert "Error" in result
        assert "not found" in result.lower()

    def test_directory_not_file(self):
        result = self.tool._run(self.TEMP_DIR)
        assert "Error" in result
        assert "Not a file" in result

    def test_large_file_rejected(self):
        """Files over 1MB are rejected."""
        file_path = os.path.join(self.TEMP_DIR, "big.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("x" * (1_048_577))
        result = self.tool._run(file_path)
        assert "Error" in result
        assert "too large" in result.lower()


# --- WebSearchTool Tests ---

from app.tools.web_search_tool import WebSearchTool


class TestWebSearchTool:
    """Tests for the DuckDuckGo web search tool."""

    def test_run_returns_formatted_results(self):
        """_run() formats DDG results as a numbered list."""
        mock_results = [
            {"title": "Python Docs", "href": "https://python.org", "body": "Official Python documentation."},
            {"title": "PyPI", "href": "https://pypi.org", "body": "Python package index."},
        ]
        tool = WebSearchTool()
        with patch("app.tools.web_search_tool.DDGS") as MockDDGS:
            mock_ddgs_instance = MagicMock()
            mock_ddgs_instance.text.return_value = mock_results
            MockDDGS.return_value.__enter__ = MagicMock(return_value=mock_ddgs_instance)
            MockDDGS.return_value.__exit__ = MagicMock(return_value=False)

            result = tool._run("Python documentation")

        assert "1. Python Docs" in result
        assert "https://python.org" in result
        assert "Official Python documentation." in result
        assert "2. PyPI" in result

    def test_run_no_results(self):
        """_run() returns a clear message when no results are found."""
        tool = WebSearchTool()
        with patch("app.tools.web_search_tool.DDGS") as MockDDGS:
            mock_ddgs_instance = MagicMock()
            mock_ddgs_instance.text.return_value = []
            MockDDGS.return_value.__enter__ = MagicMock(return_value=mock_ddgs_instance)
            MockDDGS.return_value.__exit__ = MagicMock(return_value=False)

            result = tool._run("xyzzy nonexistent query")

        assert "No results found" in result

    def test_run_handles_exception(self):
        """_run() returns an error string rather than raising on failure."""
        tool = WebSearchTool()
        with patch("app.tools.web_search_tool.DDGS") as MockDDGS:
            MockDDGS.side_effect = Exception("Network error")
            result = tool._run("any query")

        assert "Web search failed" in result
        assert "Network error" in result

    def test_tool_name_and_description(self):
        """Tool has correct name and non-empty description."""
        tool = WebSearchTool()
        assert tool.name == "web_search"
        assert len(tool.description) > 10


# --- NotionTool Tests ---

from app.tools.notion_tool import NotionTool


class TestNotionTool:
    """Tests for the Notion read/write tool."""

    def _make_tool(self):
        return NotionTool()

    def test_search_returns_results(self):
        """search action formats page titles and IDs."""
        tool = self._make_tool()
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [
                {
                    "object": "page",
                    "id": "abc-123",
                    "url": "https://notion.so/abc-123",
                    "properties": {
                        "title": {
                            "title": [{"plain_text": "My Project"}]
                        }
                    },
                }
            ]
        }
        with patch.object(tool, "_get_client", return_value=mock_client):
            result = tool._run(action="search", query="My Project")

        assert "My Project" in result
        assert "abc-123" in result

    def test_search_no_results(self):
        """search action handles empty results."""
        tool = self._make_tool()
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}
        with patch.object(tool, "_get_client", return_value=mock_client):
            result = tool._run(action="search", query="nonexistent page")

        assert "No Notion pages found" in result

    def test_search_requires_query(self):
        """search action returns error when query is empty."""
        tool = self._make_tool()
        result = tool._run(action="search", query="")
        assert "requires a query" in result

    def test_get_page_returns_content(self):
        """get_page fetches title and block text."""
        tool = self._make_tool()
        mock_client = MagicMock()
        mock_client.pages.retrieve.return_value = {
            "id": "page-999",
            "properties": {
                "title": {"title": [{"plain_text": "Test Page"}]}
            },
        }
        mock_client.blocks.children.list.return_value = {
            "results": [
                {
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"plain_text": "Hello world"}]
                    },
                }
            ]
        }
        with patch.object(tool, "_get_client", return_value=mock_client):
            result = tool._run(action="get_page", page_id="page-999")

        assert "Test Page" in result
        assert "Hello world" in result

    def test_get_page_requires_page_id(self):
        """get_page returns error when page_id is empty."""
        tool = self._make_tool()
        result = tool._run(action="get_page", page_id="")
        assert "requires page_id" in result

    def test_create_page_success(self):
        """create_page returns new page ID and URL."""
        tool = self._make_tool()
        mock_client = MagicMock()
        mock_client.pages.create.return_value = {
            "id": "new-page-id",
            "url": "https://notion.so/new-page-id",
        }
        with patch.object(tool, "_get_client", return_value=mock_client):
            result = tool._run(
                action="create_page",
                title="New Page",
                content="Some content",
                parent_page_id="parent-123",
            )

        assert "created successfully" in result
        assert "new-page-id" in result

    def test_create_page_requires_title(self):
        """create_page returns error when title is missing."""
        tool = self._make_tool()
        result = tool._run(action="create_page", title="", content="text", parent_page_id="pid")
        assert "requires a title" in result

    def test_create_page_requires_content(self):
        """create_page returns error when content is missing."""
        tool = self._make_tool()
        result = tool._run(action="create_page", title="T", content="", parent_page_id="pid")
        assert "requires content" in result

    def test_append_blocks_success(self):
        """append_blocks confirms successful append."""
        tool = self._make_tool()
        mock_client = MagicMock()
        with patch.object(tool, "_get_client", return_value=mock_client):
            result = tool._run(action="append_blocks", page_id="pg-1", content="New paragraph")

        assert "appended" in result
        assert "pg-1" in result
        mock_client.blocks.children.append.assert_called_once()

    def test_append_blocks_requires_page_id(self):
        """append_blocks returns error when page_id is missing."""
        tool = self._make_tool()
        result = tool._run(action="append_blocks", page_id="", content="text")
        assert "requires page_id" in result

    def test_unknown_action_returns_error(self):
        """Unknown action returns a clear error message."""
        tool = self._make_tool()
        result = tool._run(action="delete_everything")
        assert "Unknown action" in result

    def test_tool_name_and_description(self):
        """Tool has correct name and non-empty description."""
        tool = self._make_tool()
        assert tool.name == "notion"
        assert len(tool.description) > 10
