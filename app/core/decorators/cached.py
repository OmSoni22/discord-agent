from functools import wraps
from typing import Type, Union, List
from pydantic import BaseModel

def cached(key_builder, ttl: int = 60, model: Union[Type[BaseModel], None] = None):
    """
    Decorator to cache the result of an async method.
    Expects the instance (self) to have a 'cache_service' attribute.
    """
    def wrapper(func):
        @wraps(func)
        async def inner(*args, **kwargs):
            # Inspect args[0] for 'self'
            instance = args[0] if args else None
            cache_service = getattr(instance, "cache_service", None)
            
            if not cache_service:
                return await func(*args, **kwargs)

            key = key_builder(*args, **kwargs)
            cached_val = await cache_service.get(key)
            
            if cached_val is not None:
                # If we have a model, verify/convert back to objects
                if model:
                    if isinstance(cached_val, list):
                        return [model(**item) for item in cached_val]
                    return model(**cached_val)
                return cached_val

            result = await func(*args, **kwargs)
            await cache_service.set(key, result, ttl=ttl)
            return result
        return inner
    return wrapper

