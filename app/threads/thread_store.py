"""Thread Store — persistent PostgreSQL-backed conversation storage.

Replaces the old InMemorySessionStore. Each thread = one conversation.
"""

from __future__ import annotations

import logging
import uuid
from typing import Protocol

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.threads.models import Thread, Message

logger = logging.getLogger(__name__)


class BaseThreadStore(Protocol):
    """Abstract interface for thread storage (Dependency Inversion)."""

    async def create_thread(self, title: str | None = None) -> Thread: ...
    async def get_thread(self, thread_id: str) -> Thread | None: ...
    async def list_threads(self, limit: int = 50, offset: int = 0) -> list[Thread]: ...
    async def delete_thread(self, thread_id: str) -> bool: ...
    async def add_message(self, thread_id: str, role: str, content: str, **kwargs) -> Message: ...
    async def get_messages(self, thread_id: str) -> list[Message]: ...


class ThreadStore:
    """PostgreSQL-backed thread store using async SQLAlchemy.

    All operations require an AsyncSession from the DI system.
    """

    def __init__(self, session_factory) -> None:
        """Initialize with an async session factory (async_sessionmaker)."""
        self._session_factory = session_factory

    async def create_thread(self, title: str | None = None) -> Thread:
        """Create a new conversation thread."""
        async with self._session_factory() as session:
            thread = Thread(title=title)
            session.add(thread)
            await session.commit()
            await session.refresh(thread)
            logger.info("Thread created: %s", thread.id)
            return thread

    async def get_thread(self, thread_id: str) -> Thread | None:
        """Get a thread by ID with its messages loaded."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(Thread).where(Thread.id == thread_id)
            )
            thread = result.scalar_one_or_none()
            if thread:
                # Force-load messages (selectin should handle this, but be explicit)
                _ = thread.messages
            return thread

    async def list_threads(self, limit: int = 50, offset: int = 0) -> list[Thread]:
        """List threads ordered by most recent first."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(Thread)
                .order_by(Thread.updated_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())

    async def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread and all its messages (CASCADE)."""
        async with self._session_factory() as session:
            result = await session.execute(
                delete(Thread).where(Thread.id == thread_id)
            )
            await session.commit()
            deleted = result.rowcount > 0
            if deleted:
                logger.info("Thread deleted: %s", thread_id)
            return deleted

    async def add_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        tool_call_id: str | None = None,
        tool_name: str | None = None,
        tool_input: dict | None = None,
    ) -> Message:
        """Add a message to a thread and persist it."""
        async with self._session_factory() as session:
            message = Message(
                thread_id=thread_id,
                role=role,
                content=content,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                tool_input=tool_input,
            )
            session.add(message)

            # Update thread's updated_at
            thread = await session.get(Thread, thread_id)
            if thread:
                from datetime import datetime, timezone
                thread.updated_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(message)
            return message

    async def get_messages(self, thread_id: str) -> list[Message]:
        """Get all messages for a thread, ordered by creation time."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(Message)
                .where(Message.thread_id == thread_id)
                .order_by(Message.created_at)
            )
            return list(result.scalars().all())
