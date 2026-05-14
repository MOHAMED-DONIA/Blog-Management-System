"""
Comment Service — with Logging + Caching
"""
import math
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.cache import comments_cache
from app.core.logger import get_logger
from app.core.metrics import metrics
from app.models.comment import Comment
from app.models.post import Post
from app.models.user import User, UserRole
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate, PaginatedComments

logger = get_logger("blog_api.comments")


def _cache_key(post_id: int, page: int, size: int) -> str:
    return f"comments:{post_id}:{page}:{size}"


def _invalidate_post_comments(post_id: int) -> None:
    comments_cache.invalidate_prefix(f"comments:{post_id}:")


# ── Tree Builder ──────────────────────────────────────────────────────────────

def _build_comment_tree(comments: List[Comment]) -> List[CommentResponse]:
    """Build nested comment tree from flat list."""
    comment_map: dict = {}
    roots: List[CommentResponse] = []

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


# ── CRUD ──────────────────────────────────────────────────────────────────────

def get_post_comments(
    db: Session, post_id: int, page: int = 1, size: int = 20
) -> PaginatedComments:
    cache_key = _cache_key(post_id, page, size)

    cached = comments_cache.get(cache_key)
    if cached is not None:
        logger.debug("Cache HIT — comments post_id=%d page=%d", post_id, page)
        return cached

    _get_post_or_404(db, post_id)
    offset = (page - 1) * size
    total = (
        db.query(Comment)
        .filter(Comment.post_id == post_id, Comment.parent_id == None)  # noqa: E711
        .count()
    )
    top_level = (
        db.query(Comment)
        .filter(Comment.post_id == post_id, Comment.parent_id == None)  # noqa: E711
        .order_by(Comment.created_at.asc())
        .offset(offset)
        .limit(size)
        .all()
    )
    top_ids = [c.id for c in top_level]
    all_comments = top_level[:]
    if top_ids:
        replies = db.query(Comment).filter(Comment.parent_id.in_(top_ids)).all()
        all_comments += replies

    tree = _build_comment_tree(all_comments)
    result = PaginatedComments(
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total else 0,
        items=tree,
    )

    comments_cache.set(cache_key, result)
    logger.debug("Cache MISS — fetched comments post_id=%d page=%d (top-level=%d)", post_id, page, total)
    return result


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

    _invalidate_post_comments(post_id)

    is_reply = data.parent_id is not None
    logger.info(
        "Comment %s | id=%d post_id=%d author='%s'",
        "reply created" if is_reply else "created",
        comment.id,
        post_id,
        current_user.username,
    )
    metrics.record_op("comment_reply" if is_reply else "comment_create")
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

    _invalidate_post_comments(comment.post_id)

    logger.info(
        "Comment updated | id=%d by='%s'",
        comment_id,
        current_user.username,
    )
    metrics.record_op("comment_update")
    return comment


def delete_comment(db: Session, comment_id: int, current_user: User) -> None:
    comment = _get_comment_or_404(db, comment_id)

    if current_user.role != UserRole.ADMIN and current_user.id != comment.author_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    post_id = comment.post_id
    db.delete(comment)
    db.commit()

    _invalidate_post_comments(post_id)

    logger.info(
        "Comment deleted | id=%d by='%s'",
        comment_id,
        current_user.username,
    )
    metrics.record_op("comment_delete")


# ── Helpers ───────────────────────────────────────────────────────────────────

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
