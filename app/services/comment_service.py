import math
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.cache import comments_cache
from app.core.request_context import request_context
from app.core.logger import get_logger
from app.core.metrics import metrics
from app.models.comment import Comment
from app.models.user import User, UserRole
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate, PaginatedComments

logger = get_logger("blog_api.comments")


def _cache_key_post_comments(post_id: int, page: int, size: int) -> str:
    return f"comments:post:{post_id}:p{page}:s{size}"


def get_post_comments(
    db: Session, post_id: int, page: int = 1, size: int = 20
) -> PaginatedComments:
    cache_key = _cache_key_post_comments(post_id, page, size)

    # ── Cache HIT ─────────────────────────────────────────────────────────────
    cached = comments_cache.get(cache_key)
    if cached is not None:
        logger.info("Cache HIT — Serving comments for post_id=%d from memory", post_id)
        req = request_context.get()
        if req: req.state.cache_hit = True
        cached.source = "Cache"
        return cached

    # ── DB Query ──────────────────────────────────────────────────────────────
    logger.info("Cache MISS — Fetching comments for post_id=%d from Database", post_id)
    offset = (page - 1) * size
    query = db.query(Comment).filter(Comment.post_id == post_id, Comment.parent_id == None)
    total = query.count()
    comments = query.order_by(Comment.created_at.desc()).offset(offset).limit(size).all()

    result = PaginatedComments(
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total else 0,
        items=[CommentResponse.model_validate(c) for c in comments],
        source="Database"
    )

    comments_cache.set(cache_key, result)
    return result


from app.models.post import Post

def create_comment(
    db: Session, post_id: int, data: CommentCreate, current_user: User
) -> Comment:
    # Check if post exists
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # Check if parent exists if parent_id is provided
    if data.parent_id:
        parent = db.query(Comment).filter(Comment.id == data.parent_id).first()
        if not parent or parent.post_id != post_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parent comment"
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

    # Invalidate post comments cache
    comments_cache.invalidate_prefix(f"comments:post:{post_id}:")

    logger.info("Comment created | id=%d | post=%d | Cache invalidated", comment.id, post_id)
    metrics.record_op("comment_create")
    return comment


def update_comment(
    db: Session, comment_id: int, data: CommentUpdate, current_user: User
) -> Comment:
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    _assert_ownership_or_admin(comment.author_id, current_user)

    comment.content = data.content
    db.commit()
    db.refresh(comment)

    # Invalidate post comments cache
    comments_cache.invalidate_prefix(f"comments:post:{comment.post_id}:")

    logger.info("Comment updated | id=%d | Cache invalidated", comment_id)
    metrics.record_op("comment_update")
    return comment


def delete_comment(db: Session, comment_id: int, current_user: User) -> None:
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    _assert_ownership_or_admin(comment.author_id, current_user)

    post_id = comment.post_id
    db.delete(comment)
    db.commit()

    # Invalidate post comments cache
    comments_cache.invalidate_prefix(f"comments:post:{post_id}:")

    logger.info("Comment deleted | id=%d | Cache invalidated", comment_id)
    metrics.record_op("comment_delete")


def _assert_ownership_or_admin(author_id: int, current_user: User) -> None:
    if current_user.role != UserRole.ADMIN and current_user.id != author_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to modify this comment",
        )
