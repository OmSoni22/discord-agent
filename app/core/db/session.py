"""Async SQLAlchemy engine and session factory."""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

from app.config.settings import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Verify DB connectivity on startup. Raises on failure."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("Database connection established successfully.")
    except Exception as e:
        print(f"Failed to connect to Database: {e}")
        raise


def close_db() -> None:
    """Dispose the engine to close pool connections."""
    try:
        sync_engine = getattr(engine, "sync_engine", None)
        if sync_engine is not None:
            sync_engine.dispose()
        else:
            engine.dispose()
        print("Database engine disposed.")
    except Exception as e:
        print(f"Error disposing DB engine: {e}")
