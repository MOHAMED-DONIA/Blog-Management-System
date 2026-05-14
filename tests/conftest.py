import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test_blog.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # Clear caches between tests to prevent cross-test contamination
    from app.core.cache import posts_cache, comments_cache
    posts_cache.clear()
    comments_cache.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    client.post("/auth/register", json={
        "username": "adminuser", "email": "admin@test.com",
        "password": "admin123"
    })
    # Manually set admin role via DB
    db = TestingSessionLocal()
    from app.models.user import User, UserRole
    user = db.query(User).filter(User.username == "adminuser").first()
    user.role = UserRole.ADMIN
    db.commit()
    db.close()
    resp = client.post("/auth/login", data={"username": "adminuser", "password": "admin123"})
    return resp.json()["access_token"]


@pytest.fixture
def author_token(client):
    client.post("/auth/register", json={
        "username": "authoruser", "email": "author@test.com",
        "password": "author123"
    })
    db = TestingSessionLocal()
    from app.models.user import User, UserRole
    user = db.query(User).filter(User.username == "authoruser").first()
    user.role = UserRole.AUTHOR
    db.commit()
    db.close()
    resp = client.post("/auth/login", data={"username": "authoruser", "password": "author123"})
    return resp.json()["access_token"]


@pytest.fixture
def reader_token(client):
    client.post("/auth/register", json={
        "username": "readeruser", "email": "reader@test.com",
        "password": "reader123"
    })
    resp = client.post("/auth/login", data={"username": "readeruser", "password": "reader123"})
    return resp.json()["access_token"]
