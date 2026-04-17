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

    action: Literal[
        "search", 
        "get_page", 
        "create_page", 
        "append_blocks", 
        "update_properties", 
        "update_block", 
        "replace_content"
    ] = Field(
        description=(
            "Action to perform: 'search', 'get_page', 'create_page', 'append_blocks', "
            "'update_properties', 'update_block', or 'replace_content'."
        )
    )
    query: str = Field(default="", description="Search query — required for 'search'")
    page_id: str = Field(
        default="", description="Notion page ID — required for page-level actions"
    )
    title: str = Field(default="", description="Page title — required for 'create_page' and 'update_properties'")
    content: str = Field(
        default="", description="Text content — required for creating/updating blocks or replacing content"
    )
    parent_page_id: str = Field(
        default="",
        description=(
            "Parent page ID for 'create_page'. "
            "Falls back to NOTION_DEFAULT_PAGE_ID env var if not provided."
        ),
    )
    block_id: str = Field(
        default="", description="Notion block ID — required for 'update_block'"
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
        "Actions: search, get_page, create_page, append_blocks, "
        "update_properties (change title), update_block (change specific text element), "
        "replace_content (replace whole page)."
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
        block_id: str = "",
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
            elif action == "update_properties":
                return self._update_properties(notion, page_id, title)
            elif action == "update_block":
                return self._update_block(notion, block_id, content)
            elif action == "replace_content":
                return self._replace_content(notion, page_id, content)
            else:
                return (
                    f"Error: Unknown action '{action}'. "
                    "Valid actions: search, get_page, create_page, append_blocks, "
                    "update_properties, update_block, replace_content."
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
        block_id: str = "",
    ) -> str:
        """Async version — runs sync implementation in a thread pool."""
        import asyncio
        return await asyncio.to_thread(
            self._run, action, query, page_id, title, content, parent_page_id, block_id
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

        content_lines = []
        for b in blocks:
            text = self._extract_block_text(b)
            bid = b.get("id", "unknown-id")
            if text:
                content_lines.append(f"[Block ID: {bid}] {text}")

        content = "\n".join(content_lines) or "(empty page)"

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

    def _update_properties(self, notion, page_id: str, title: str) -> str:
        if not page_id:
            return "Error: 'update_properties' requires page_id."
        if not title:
            return "Error: 'update_properties' currently requires a title."

        notion.pages.update(
            page_id=page_id,
            properties={
                "title": {
                    "title": [{"type": "text", "text": {"content": title}}]
                }
            }
        )
        return f"Page {page_id} properties updated successfully."

    def _update_block(self, notion, block_id: str, content: str) -> str:
        if not block_id:
            return "Error: 'update_block' requires block_id."
        if not content:
            return "Error: 'update_block' requires content."

        notion.blocks.update(
            block_id=block_id,
            paragraph={
                "rich_text": [{"type": "text", "text": {"content": content}}]
            }
        )
        return f"Block {block_id} content updated successfully."

    def _replace_content(self, notion, page_id: str, content: str) -> str:
        if not page_id:
            return "Error: 'replace_content' requires page_id."
        if not content:
            return "Error: 'replace_content' requires content."

        # Fetch all children blocks
        blocks_resp = notion.blocks.children.list(block_id=page_id)
        blocks = blocks_resp.get("results", [])

        # Delete existing blocks
        for block in blocks:
            try:
                notion.blocks.delete(block_id=block["id"])
            except Exception as e:
                logger.warning("Could not delete block %s during replace operation: %s", block["id"], e)

        # Append new content
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
        
        return f"Content of page {page_id} successfully replaced."

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
