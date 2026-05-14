"""
Post Service — with Logging + Caching
"""
import math

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.cache import posts_cache
from app.core.logger import get_logger
from app.core.metrics import metrics
from app.models.post import Post
from app.models.user import User, UserRole
from app.schemas.post import PaginatedPosts, PostCreate, PostListResponse, PostUpdate

logger = get_logger("blog_api.posts")


def _cache_key_list(page: int, size: int) -> str:
    return f"posts:list:{page}:{size}"


def _cache_key_single(post_id: int) -> str:
    return f"posts:detail:{post_id}"


def get_all_posts(db: Session, page: int = 1, size: int = 10) -> PaginatedPosts:
    cache_key = _cache_key_list(page, size)

    # ── Cache HIT ─────────────────────────────────────────────────────────────
    cached = posts_cache.get(cache_key)
    if cached is not None:
        logger.debug("Cache HIT — posts list page=%d size=%d", page, size)
        return cached

    # ── DB Query ──────────────────────────────────────────────────────────────
    offset = (page - 1) * size
    total = db.query(Post).count()
    posts = db.query(Post).order_by(Post.created_at.desc()).offset(offset).limit(size).all()

    result = PaginatedPosts(
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total else 0,
        items=[PostListResponse.model_validate(p) for p in posts],
    )

    posts_cache.set(cache_key, result)
    logger.debug("Cache MISS — fetched posts list page=%d size=%d (total=%d)", page, size, total)
    return result


def get_post_by_id(db: Session, post_id: int) -> Post:
    cache_key = _cache_key_single(post_id)

    cached = posts_cache.get(cache_key)
    if cached is not None:
        logger.debug("Cache HIT — post id=%d", post_id)
        return cached

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        logger.warning("Post not found: id=%d", post_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    posts_cache.set(cache_key, post)
    logger.debug("Cache MISS — fetched post id=%d", post_id)
    return post


def create_post(db: Session, data: PostCreate, current_user: User) -> Post:
    post = Post(title=data.title, content=data.content, author_id=current_user.id)
    db.add(post)
    db.commit()
    db.refresh(post)

    # Invalidate all list caches
    posts_cache.invalidate_prefix("posts:list:")

    logger.info(
        "Post created | id=%d title='%s' author='%s'",
        post.id,
        post.title[:40],
        current_user.username,
    )
    metrics.record_op("post_create")
    return post


def update_post(db: Session, post_id: int, data: PostUpdate, current_user: User) -> Post:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    _assert_ownership_or_admin(post.author_id, current_user)

    if data.title is not None:
        post.title = data.title
    if data.content is not None:
        post.content = data.content
    db.commit()
    db.refresh(post)

    # Invalidate caches for this post and all list pages
    posts_cache.delete(_cache_key_single(post_id))
    posts_cache.invalidate_prefix("posts:list:")

    logger.info(
        "Post updated | id=%d by='%s'",
        post_id,
        current_user.username,
    )
    metrics.record_op("post_update")
    return post


def delete_post(db: Session, post_id: int, current_user: User) -> None:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete posts",
        )

    db.delete(post)
    db.commit()

    posts_cache.delete(_cache_key_single(post_id))
    posts_cache.invalidate_prefix("posts:list:")

    logger.info(
        "Post deleted | id=%d by='%s'",
        post_id,
        current_user.username,
    )
    metrics.record_op("post_delete")


def _assert_ownership_or_admin(author_id: int, current_user: User) -> None:
    if current_user.role != UserRole.ADMIN and current_user.id != author_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this resource",
        )
