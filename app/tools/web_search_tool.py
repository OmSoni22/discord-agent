"""Web Search Tool — searches the web using DuckDuckGo (free, no API key)."""

from __future__ import annotations

import logging
from typing import Type

from ddgs import DDGS
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WebSearchInput(BaseModel):
    """Input schema for the web search tool."""

    query: str = Field(description="The search query to look up on the web")


class WebSearchTool(BaseTool):
    """Search the web for current information using DuckDuckGo.

    Use this when you need facts, news, recent events, or anything that
    requires looking up information on the internet. Returns top 5 results
    with title, URL, and a short snippet. Free — no API key required.
    """

    name: str = "web_search"
    description: str = "Search the web for current information, facts, and news."
    args_schema: Type[BaseModel] = WebSearchInput

    def _run(self, query: str) -> str:
        """Run a DuckDuckGo search and return formatted results."""
        logger.info("Web search query: %s", query)
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))

            if not results:
                return "No results found."

            lines = []
            for i, r in enumerate(results, 1):
                title = r.get("title", "No title")
                url = r.get("href", "")
                body = r.get("body", "")
                lines.append(f"{i}. {title}\n   URL: {url}\n   {body}")

            results_str = "\n\n".join(lines)
            logger.info("Search results summary: %s", results_str[:150] + "..." if len(results_str) > 150 else results_str)
            return results_str

        except Exception as e:
            error_msg = f"Web search failed: {e}"
            logger.error(error_msg)
            return error_msg

    async def _arun(self, query: str) -> str:
        """Async version — runs sync search in a thread pool."""
        import asyncio
        return await asyncio.to_thread(self._run, query)
