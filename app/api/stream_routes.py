"""Thread and streaming API routes."""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Query, Request, HTTPException, Body
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.streaming.sse_handler import SSEHandler

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Agent"])


# --- Request/Response schemas ---

class CreateThreadRequest(BaseModel):
    """Request body for creating a new thread."""
    title: str | None = Field(None, description="Optional title for the thread")


class ThreadResponse(BaseModel):
    """Response for a thread."""
    id: str
    title: str | None
    created_at: str
    updated_at: str
    message_count: int = 0


class MessageResponse(BaseModel):
    """Response for a single message."""
    id: str
    role: str
    content: str
    tool_name: str | None = None
    tool_input: dict | None = None
    created_at: str


# --- Thread CRUD endpoints ---

@router.post("/threads", response_model=ThreadResponse)
async def create_thread(
    request: Request,
    body: CreateThreadRequest = Body(default=CreateThreadRequest(), examples=[{"title": "My Thread"}]),
):
    """Create a new conversation thread."""
    thread_store = request.app.state.thread_store
    thread = await thread_store.create_thread(title=body.title)
    return ThreadResponse(
        id=thread.id,
        title=thread.title,
        created_at=thread.created_at.isoformat(),
        updated_at=thread.updated_at.isoformat(),
        message_count=0,
    )


@router.get("/threads", response_model=list[ThreadResponse])
async def list_threads(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List all conversation threads."""
    thread_store = request.app.state.thread_store
    threads = await thread_store.list_threads(limit=limit, offset=offset)
    return [
        ThreadResponse(
            id=t.id,
            title=t.title,
            created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat(),
            message_count=len(t.messages) if t.messages else 0,
        )
        for t in threads
    ]


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(request: Request, thread_id: str):
    """Get a thread's details."""
    thread_store = request.app.state.thread_store
    thread = await thread_store.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")
    return ThreadResponse(
        id=thread.id,
        title=thread.title,
        created_at=thread.created_at.isoformat(),
        updated_at=thread.updated_at.isoformat(),
        message_count=len(thread.messages) if thread.messages else 0,
    )


@router.delete("/threads/{thread_id}")
async def delete_thread(request: Request, thread_id: str):
    """Delete a thread and all its messages."""
    thread_store = request.app.state.thread_store
    deleted = await thread_store.delete_thread(thread_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")
    return {"deleted": True, "thread_id": thread_id}


@router.get("/threads/{thread_id}/messages", response_model=list[MessageResponse])
async def get_thread_messages(request: Request, thread_id: str):
    """Get all messages in a thread."""
    thread_store = request.app.state.thread_store

    # Verify thread exists
    thread = await thread_store.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")

    messages = await thread_store.get_messages(thread_id)
    return [
        MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            tool_name=msg.tool_name,
            tool_input=msg.tool_input,
            created_at=msg.created_at.isoformat(),
        )
        for msg in messages
    ]


# --- SSE Streaming endpoint ---

@router.get("/threads/{thread_id}/stream")
async def stream_agent(
    request: Request,
    thread_id: str,
    query: str = Query(..., description="User query to send to the agent"),
):
    """SSE endpoint — streams the agent's ReAct loop in real time.

    The thread must be created first via POST /threads.
    All messages are persisted to the database.

    Content-Type: text/event-stream
    Cache-Control: no-cache
    Connection: keep-alive
    """
    thread_store = request.app.state.thread_store

    # Verify thread exists
    thread = await thread_store.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")

    agent_runner = request.app.state.agent_runner
    sse_handler: SSEHandler = request.app.state.sse_handler

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            async for event in agent_runner.run(thread_id, query):
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info("Client disconnected, stopping stream")
                    break

                yield sse_handler.format_event(event)
        except Exception as e:
            logger.error("Stream error: %s", e, exc_info=True)
            error_event = {
                "type": "error",
                "message": str(e),
                "source_agent": "primary",
            }
            yield sse_handler.format_event(error_event)

    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
    )
