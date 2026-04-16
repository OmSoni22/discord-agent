"""Base tool interface — all tools extend LangChain's BaseTool."""

# Tools use LangChain's built-in BaseTool directly.
# No custom abstract class needed — LangChain handles:
#   - name, description, args_schema
#   - _run() / _arun() pattern
#   - Pydantic input validation
#
# Import path for tool authors:
#   from langchain_core.tools import BaseTool
#   from pydantic import BaseModel, Field
