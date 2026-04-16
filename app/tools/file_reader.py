"""File reader tool — reads files from the local filesystem."""

from __future__ import annotations

import logging
import os
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Maximum file size to read (1 MB)
MAX_FILE_SIZE = 1_048_576


class FileReaderInput(BaseModel):
    """Input schema for the file reader tool."""
    file_path: str = Field(
        description="Absolute or relative path to the file to read"
    )


class FileReaderTool(BaseTool):
    """Read the contents of a file from the local filesystem.

    Use this tool when you need to examine the contents of a text file,
    configuration file, source code, or any other readable file.
    """

    name: str = "file_reader"
    description: str = (
        "Read the contents of a file from the local filesystem. "
        "Use when the user asks you to look at, read, or examine a file. "
        "Provide the file path as input. Returns the file content as text."
    )
    args_schema: Type[BaseModel] = FileReaderInput

    def _run(self, file_path: str) -> str:
        """Read and return file contents."""
        logger.info("Reading file: %s", file_path)

        # Resolve to absolute path
        abs_path = os.path.abspath(file_path)

        # Existence check
        if not os.path.exists(abs_path):
            return f"Error: File not found: {abs_path}"

        if not os.path.isfile(abs_path):
            return f"Error: Not a file: {abs_path}"

        # Size check
        size = os.path.getsize(abs_path)
        if size > MAX_FILE_SIZE:
            return f"Error: File too large ({size:,} bytes). Max allowed: {MAX_FILE_SIZE:,} bytes."

        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()
            return content
        except UnicodeDecodeError:
            return f"Error: Cannot read binary file: {abs_path}"
        except PermissionError:
            return f"Error: Permission denied: {abs_path}"
        except Exception as e:
            error_msg = f"Error reading file '{abs_path}': {e}"
            logger.error(error_msg)
            return error_msg

    async def _arun(self, file_path: str) -> str:
        """Async version — delegates to sync (I/O is fast for small files)."""
        return self._run(file_path)
