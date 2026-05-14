"""
Blog Management System — Application Entry Point
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.core.config import settings
from app.core.logger import app_logger as logger
from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.middleware.logging_middleware import LoggingMiddleware
from app.routes import auth, comments, posts, users
from app.routes import monitoring

# ── Database Bootstrap ────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)


def create_default_admin() -> None:
    """Ensure a default admin account exists on first run."""
    from app.models.user import User, UserRole

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if not existing:
            admin = User(
                username="admin",
                email="admin@blog.com",
                hashed_password=hash_password("admin123"),
                role=UserRole.ADMIN,
            )
            db.add(admin)
            db.commit()
            logger.info("Default admin created: username=admin | password=admin123")
    finally:
        db.close()


create_default_admin()

# ── App Factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "A fully-featured Blog Management System with JWT Auth, "
        "Role-Based Access Control, Request Logging, In-Memory Caching, "
        "and a real-time Monitoring Dashboard."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────────────
# NOTE: Middleware is applied in REVERSE order — LoggingMiddleware wraps last.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(monitoring.router)

# ── Static Frontend ───────────────────────────────────────────────────────────
try:
    app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")
except RuntimeError:
    pass  # frontend dir may not exist in tests

# ── Global Exception Handlers ─────────────────────────────────────────────────


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ── Health Check ──────────────────────────────────────────────────────────────


@app.get("/", tags=["Health"])
def root():
    logger.debug("Health check requested")
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs": "/docs",
        "metrics_dashboard": "/metrics/dashboard (admin only)",
    }
