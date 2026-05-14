from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator

from app.schemas.user import UserResponse


class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1:
            raise ValueError("Comment content cannot be empty")
        if len(v) > 2000:
            raise ValueError("Comment must not exceed 2000 characters")
        return v


class CommentUpdate(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1:
            raise ValueError("Comment content cannot be empty")
        if len(v) > 2000:
            raise ValueError("Comment must not exceed 2000 characters")
        return v


class CommentResponse(BaseModel):
    id: int
    content: str
    post_id: int
    author_id: int
    parent_id: Optional[int]
    author: UserResponse
    created_at: datetime
    updated_at: Optional[datetime] = None
    replies: List[CommentResponse] = []

    model_config = {"from_attributes": True}


class PaginatedComments(BaseModel):
    total: int
    page: int
    size: int
    pages: int
    items: List[CommentResponse]
