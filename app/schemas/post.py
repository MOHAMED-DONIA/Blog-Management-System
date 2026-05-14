from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator

from app.schemas.user import UserResponse


class ResponseMetadata(BaseModel):
    source: str  # "Database" or "Cache"
    response_time_ms: str


class PostCreate(BaseModel):
    title: str
    content: str

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Title must be at least 3 characters")
        return v

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Content must be at least 10 characters")
        return v


class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    author: UserResponse
    created_at: datetime
    updated_at: Optional[datetime] = None
    _metadata: Optional[ResponseMetadata] = None  # Internal use

    model_config = {"from_attributes": True}


class PostListResponse(BaseModel):
    id: int
    title: str
    author_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedPosts(BaseModel):
    total: int
    page: int
    size: int
    pages: int
    items: List[PostListResponse]
    source: str = "Database"  # Added field to show in API
