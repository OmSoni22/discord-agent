"""Notion Tool — interact with Notion pages (search, read, create, append)."""

from __future__ import annotations

import logging
from typing import Type, Literal

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.config.settings import settings

logger = logging.getLogger(__name__)


class NotionInput(BaseModel):
    """Input schema for the Notion tool."""

    action: Literal["search", "get_page", "create_page", "append_blocks"] = Field(
        description=(
            "Action to perform: 'search' (find pages), 'get_page' (read content), "
            "'create_page' (new page), or 'append_blocks' (add text)."
        )
    )
    query: str = Field(default="", description="Search query — required for 'search'")
    page_id: str = Field(
        default="", description="Notion page ID — required for 'get_page' and 'append_blocks'"
    )
    title: str = Field(default="", description="Page title — required for 'create_page'")
    content: str = Field(
        default="", description="Text content — required for 'create_page' and 'append_blocks'"
    )
    parent_page_id: str = Field(
        default="",
        description=(
            "Parent page ID for 'create_page'. "
            "Falls back to NOTION_DEFAULT_PAGE_ID env var if not provided."
        ),
    )


class NotionTool(BaseTool):
    """Interact with Notion pages.

    Supports four actions:
    - search:        Find pages in your Notion workspace by query text
    - get_page:      Read the full text content of a specific page (requires page_id)
    - create_page:   Create a new page with a title and body text (requires title + content)
    - append_blocks: Add more text to an existing page (requires page_id + content)
    """

    name: str = "notion"
    description: str = (
        "Interact with Notion pages. "
        "Actions: search (find pages by query), "
        "get_page (read page content — needs page_id), "
        "create_page (create new page — needs title + content), "
        "append_blocks (add content to existing page — needs page_id + content)."
    )
    args_schema: Type[BaseModel] = NotionInput

    def _get_client(self):
        """Create a Notion API client using the configured API key."""
        from notion_client import Client
        return Client(auth=settings.notion_api_key)

    def _run(
        self,
        action: str,
        query: str = "",
        page_id: str = "",
        title: str = "",
        content: str = "",
        parent_page_id: str = "",
    ) -> str:
        """Dispatch the requested Notion action."""
        logger.info("Notion action: %s", action)
        try:
            notion = self._get_client()
            if action == "search":
                return self._search(notion, query)
            elif action == "get_page":
                return self._get_page(notion, page_id)
            elif action == "create_page":
                return self._create_page(notion, title, content, parent_page_id)
            elif action == "append_blocks":
                return self._append_blocks(notion, page_id, content)
            else:
                return (
                    f"Error: Unknown action '{action}'. "
                    "Valid actions: search, get_page, create_page, append_blocks."
                )
        except Exception as e:
            error_msg = f"Notion error ({action}): {e}"
            logger.error(error_msg)
            return error_msg

    async def _arun(
        self,
        action: str,
        query: str = "",
        page_id: str = "",
        title: str = "",
        content: str = "",
        parent_page_id: str = "",
    ) -> str:
        """Async version — runs sync implementation in a thread pool."""
        import asyncio
        return await asyncio.to_thread(
            self._run, action, query, page_id, title, content, parent_page_id
        )

    # ── private action implementations ──────────────────────────────────

    def _search(self, notion, query: str) -> str:
        if not query:
            return "Error: 'search' requires a query."

        resp = notion.search(query=query, page_size=10)
        results = resp.get("results", [])

        if not results:
            return f"No Notion pages found for: '{query}'"

        lines = []
        for r in results:
            obj_type = r.get("object", "unknown")
            rid = r.get("id", "")
            url = r.get("url", "")
            title_val = self._extract_title(r.get("properties", {}))
            lines.append(
                f"- {title_val or '(Untitled)'} [{obj_type}]\n"
                f"  ID: {rid}\n"
                f"  URL: {url}"
            )

        return f"Found {len(results)} result(s):\n" + "\n".join(lines)

    def _get_page(self, notion, page_id: str) -> str:
        if not page_id:
            return "Error: 'get_page' requires page_id."

        page = notion.pages.retrieve(page_id=page_id)
        title_val = self._extract_title(page.get("properties", {}))

        blocks_resp = notion.blocks.children.list(block_id=page_id)
        blocks = blocks_resp.get("results", [])

        content_lines = [self._extract_block_text(b) for b in blocks]
        content = "\n".join(line for line in content_lines if line) or "(empty page)"

        return f"Page: {title_val or '(Untitled)'}\nID: {page_id}\n\n{content}"

    def _create_page(
        self, notion, title: str, content: str, parent_page_id: str
    ) -> str:
        if not title:
            return "Error: 'create_page' requires a title."
        if not content:
            return "Error: 'create_page' requires content."

        parent_id = parent_page_id or settings.notion_default_page_id
        if not parent_id:
            return (
                "Error: No parent_page_id provided and "
                "NOTION_DEFAULT_PAGE_ID is not configured."
            )

        new_page = notion.pages.create(
            parent={"type": "page_id", "page_id": parent_id},
            properties={
                "title": {
                    "title": [{"type": "text", "text": {"content": title}}]
                }
            },
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content}}]
                    },
                }
            ],
        )

        page_id = new_page.get("id", "")
        url = new_page.get("url", "")
        return f"Page created successfully!\nTitle: {title}\nID: {page_id}\nURL: {url}"

    def _append_blocks(self, notion, page_id: str, content: str) -> str:
        if not page_id:
            return "Error: 'append_blocks' requires page_id."
        if not content:
            return "Error: 'append_blocks' requires content."

        notion.blocks.children.append(
            block_id=page_id,
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content}}]
                    },
                }
            ],
        )
        return f"Content appended to page {page_id} successfully."

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _extract_title(properties: dict) -> str:
        """Extract plain-text title from a Notion page's properties dict."""
        for key in ("title", "Name", "Title"):
            if key in properties:
                parts = properties[key].get("title", [])
                return "".join(p.get("plain_text", "") for p in parts)
        return ""

    @staticmethod
    def _extract_block_text(block: dict) -> str:
        """Extract plain text from a single Notion block."""
        block_type = block.get("type", "")
        block_data = block.get(block_type, {})
        rich_text = block_data.get("rich_text", [])
        return "".join(t.get("plain_text", "") for t in rich_text)
