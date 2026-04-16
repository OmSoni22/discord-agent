from functools import wraps
from app.core.db.session import AsyncSessionLocal

def transactional():
    def wrapper(func):
        @wraps(func)
        async def inner(*args, **kwargs):
            async with AsyncSessionLocal() as session:
                try:
                    kwargs["session"] = session
                    result = await func(*args, **kwargs)
                    await session.commit()
                    return result
                except Exception:
                    await session.rollback()
                    raise
        return inner
    return wrapper
