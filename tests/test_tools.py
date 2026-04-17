"""Tests for built-in tools (Calculator, FileReader, WebSearch)."""

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
