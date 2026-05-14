import math
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.cache import posts_cache
from app.core.request_context import request_context
from app.core.logger import get_logger
from app.core.metrics import metrics
from app.models.post import Post
from app.models.user import User, UserRole
from app.schemas.post import PaginatedPosts, PostCreate, PostListResponse, PostUpdate

logger = get_logger("blog_api.posts")


def _cache_key_list(page: int, size: int) -> str:
    return f"posts:list:p{page}:s{size}"


def _cache_key_single(post_id: int) -> str:
    return f"posts:item:{post_id}"


def get_all_posts(db: Session, page: int = 1, size: int = 10) -> PaginatedPosts:
    cache_key = _cache_key_list(page, size)

    # ── Cache HIT ─────────────────────────────────────────────────────────────
    cached = posts_cache.get(cache_key)
    if cached is not None:
        logger.info("Cache HIT — Serving posts list from memory")
        req = request_context.get()
        if req: req.state.cache_hit = True
        cached.source = "Cache"  # Indicate in JSON
        return cached

    # ── DB Query ──────────────────────────────────────────────────────────────
    logger.info("Cache MISS — Fetching posts list from Database")
    offset = (page - 1) * size
    total = db.query(Post).count()
    posts = db.query(Post).order_by(Post.created_at.desc()).offset(offset).limit(size).all()

    result = PaginatedPosts(
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total else 0,
        items=[PostListResponse.model_validate(p) for p in posts],
        source="Database"
    )

    posts_cache.set(cache_key, result)
    return result


def get_post_by_id(db: Session, post_id: int) -> Post:
    cache_key = _cache_key_single(post_id)

    cached = posts_cache.get(cache_key)
    if cached is not None:
        logger.info("Cache HIT — Serving post id=%d from memory", post_id)
        req = request_context.get()
        if req: req.state.cache_hit = True
        return cached

    logger.info("Cache MISS — Fetching post id=%d from Database", post_id)
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    posts_cache.set(cache_key, post)
    return post


def create_post(db: Session, data: PostCreate, current_user: User) -> Post:
    post = Post(title=data.title, content=data.content, author_id=current_user.id)
    db.add(post)
    db.commit()
    db.refresh(post)

    # Invalidate caches
    posts_cache.invalidate_prefix("posts:list:")
    
    logger.info("New post created | id=%d | Database updated", post.id)
    metrics.record_op("post_create")
    return post


def update_post(db: Session, post_id: int, data: PostUpdate, current_user: User) -> Post:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    _assert_ownership_or_admin(post.author_id, current_user)

    if data.title is not None: post.title = data.title
    if data.content is not None: post.content = data.content
    
    db.commit()
    db.refresh(post)

    # Invalidate caches
    posts_cache.delete(_cache_key_single(post_id))
    posts_cache.invalidate_prefix("posts:list:")

    logger.info("Post updated | id=%d | Cache invalidated", post_id)
    metrics.record_op("post_update")
    return post


def delete_post(db: Session, post_id: int, current_user: User) -> None:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    _assert_ownership_or_admin(post.author_id, current_user)

    db.delete(post)
    db.commit()

    # Invalidate caches
    posts_cache.delete(_cache_key_single(post_id))
    posts_cache.invalidate_prefix("posts:list:")

    logger.info("Post deleted | id=%d | Cache invalidated", post_id)
    metrics.record_op("post_delete")


def _assert_ownership_or_admin(author_id: int, current_user: User) -> None:
    if current_user.role != UserRole.ADMIN and current_user.id != author_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to modify this post",
        )
