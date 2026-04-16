"""
Centralized dependency injection for FastAPI routes.

This module provides reusable dependency functions for:
- Database session management
- Current user (for future auth)
- Pagination
- Common services
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.core.db.session import AsyncSessionLocal

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Yields:
        AsyncSession: Database session with automatic cleanup
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

class Pagination:
    """Pagination parameters for list endpoints."""
    
    def __init__(self, page: int = 1, size: int = 50):
        self.page = max(1, page)
        self.size = min(100, max(1, size))  # Max 100 items per page
        
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size
        
    @property
    def limit(self) -> int:
        return self.size
