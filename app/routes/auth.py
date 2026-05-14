from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import user as user_schema
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=user_schema.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: user_schema.UserCreate, db: Session = Depends(get_db)):
    """Register a new user (Reader by default)."""
    return auth_service.register_user(db, user_data)


@router.post("/login", response_model=user_schema.Token)
def login(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """Login and receive JWT access and refresh tokens."""
    return auth_service.authenticate_user(db, form_data.username, form_data.password)


@router.post("/refresh", response_model=user_schema.Token)
def refresh_token(
    refresh_data: user_schema.RefreshTokenRequest, db: Session = Depends(get_db)
):
    """Refresh an access token using a valid refresh token."""
    result = auth_service.refresh_access_token(db, refresh_data.refresh_token)
    return {**result, "refresh_token": refresh_data.refresh_token}
