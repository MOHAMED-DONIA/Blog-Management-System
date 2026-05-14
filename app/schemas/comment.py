from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator


class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Content cannot be empty")
        if len(v) < 2:
            raise ValueError("Content too short")
        return v


class CommentUpdate(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Content cannot be empty")
        return v


class CommentResponse(BaseModel):
    id: int
    content: str
    post_id: int
    author_id: int
    parent_id: Optional[int] = None
    created_at: datetime
    replies: List["CommentResponse"] = []

    model_config = {"from_attributes": True}


class PaginatedComments(BaseModel):
    total: int
    page: int
    size: int
    pages: int
    items: List[CommentResponse]
    source: str = "Database"
