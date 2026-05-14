from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_admin, require_author_or_admin
from app.database import get_db
from app.models.user import User
from app.schemas.post import PaginatedPosts, PostCreate, PostResponse, PostUpdate
from app.services import post_service

router = APIRouter(prefix="/posts", tags=["Posts"])


@router.get("/", response_model=PaginatedPosts)
def list_posts(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Public: list all posts with pagination."""
    return post_service.get_all_posts(db, page, size)


@router.get("/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):
    """Public: get a single post by ID."""
    return post_service.get_post_by_id(db, post_id)


@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    data: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_author_or_admin),
):
    """Author/Admin: create a new post."""
    return post_service.create_post(db, data, current_user)


@router.put("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    data: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_author_or_admin),
):
    """Author (own posts) / Admin: update a post."""
    return post_service.update_post(db, post_id, data, current_user)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin only: delete a post."""
    post_service.delete_post(db, post_id, current_user)
