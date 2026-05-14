from contextvars import ContextVar
from typing import Optional
from fastapi import Request

# Context variable to hold the current request object
request_context: ContextVar[Optional[Request]] = ContextVar("request_context", default=None)
