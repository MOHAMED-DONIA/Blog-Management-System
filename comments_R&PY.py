from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate, PaginatedComments
from app.services import comment_service

router = APIRouter(prefix="/posts/{post_id}/comments", tags=["Comments"])


@router.get("/", response_model=PaginatedComments)
def list_comments(
    post_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Public: list comments (nested) for a post."""
    return comment_service.get_post_comments(db, post_id, page, size)


@router.post("/", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    post_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Authenticated users: add a comment (or reply with parent_id)."""
    return comment_service.create_comment(db, post_id, data, current_user)


@router.put("/{comment_id}", response_model=CommentResponse)
def update_comment(
    post_id: int,
    comment_id: int,
    data: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Comment owner or Admin: update a comment."""
    return comment_service.update_comment(db, comment_id, data, current_user)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    post_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Comment owner or Admin: delete a comment."""
    comment_service.delete_comment(db, comment_id, current_user)








from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.user import UserResponse


class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None


class CommentUpdate(BaseModel):
    content: str


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







import math

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.post import Post
from app.models.user import User, UserRole
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate, PaginatedComments


def _build_comment_tree(comments: list[Comment]) -> list[CommentResponse]:
    """Build nested comment tree from flat list."""
    comment_map: dict[int, CommentResponse] = {}
    roots: list[CommentResponse] = []

    for c in comments:
        cr = CommentResponse.model_validate(c)
        cr.replies = []
        comment_map[c.id] = cr

    for c in comments:
        if c.parent_id and c.parent_id in comment_map:
            comment_map[c.parent_id].replies.append(comment_map[c.id])
        elif not c.parent_id:
            roots.append(comment_map[c.id])

    return roots


def get_post_comments(
    db: Session, post_id: int, page: int = 1, size: int = 20
) -> PaginatedComments:
    _get_post_or_404(db, post_id)
    offset = (page - 1) * size
    total = db.query(Comment).filter(Comment.post_id == post_id, Comment.parent_id == None).count()
    top_level = (
        db.query(Comment)
        .filter(Comment.post_id == post_id, Comment.parent_id == None)
        .order_by(Comment.created_at.asc())
        .offset(offset)
        .limit(size)
        .all()
    )
    # Eager-load all replies for these top-level comments
    top_ids = [c.id for c in top_level]
    all_comments = top_level[:]
    if top_ids:
        replies = (
            db.query(Comment).filter(Comment.parent_id.in_(top_ids)).all()
        )
        all_comments += replies

    tree = _build_comment_tree(all_comments)
    return PaginatedComments(
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total else 0,
        items=tree,
    )


def create_comment(
    db: Session, post_id: int, data: CommentCreate, current_user: User
) -> Comment:
    _get_post_or_404(db, post_id)
    if data.parent_id:
        parent = db.query(Comment).filter(Comment.id == data.parent_id).first()
        if not parent or parent.post_id != post_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid parent comment",
            )
    comment = Comment(
        content=data.content,
        post_id=post_id,
        author_id=current_user.id,
        parent_id=data.parent_id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def update_comment(
    db: Session, comment_id: int, data: CommentUpdate, current_user: User
) -> Comment:
    comment = _get_comment_or_404(db, comment_id)
    if current_user.role != UserRole.ADMIN and current_user.id != comment.author_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    comment.content = data.content
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, comment_id: int, current_user: User) -> None:
    comment = _get_comment_or_404(db, comment_id)
    if current_user.role != UserRole.ADMIN and current_user.id != comment.author_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    db.delete(comment)
    db.commit()


def _get_post_or_404(db: Session, post_id: int) -> Post:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return post


def _get_comment_or_404(db: Session, comment_id: int) -> Comment:
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    return comment
