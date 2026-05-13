from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.core.config import settings
from app.core.security import hash_password
from app.database import Base, engine, SessionLocal
from app.routes import auth, comments, posts, users

# Create all DB tables on startup
Base.metadata.create_all(bind=engine)

# Create default admin if not exists
def create_default_admin():
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
            print("✅ Default admin created: username=admin, password=admin123")
    finally:
        db.close()

create_default_admin()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="A fully-featured Blog Management System with JWT Auth and Role-Based Access Control.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(comments.router)

# Serve frontend
try:
    app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")
except RuntimeError:
    pass  # frontend dir may not exist in tests


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.get("/", tags=["Health"])
def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}", "docs": "/docs"}
