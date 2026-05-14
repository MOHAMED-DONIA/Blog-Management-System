from contextvars import ContextVar
from typing import Optional

# Context variable to track if the current request was served from cache
cache_hit_context: ContextVar[Optional[bool]] = ContextVar("cache_hit", default=None)
