"""
Tests for Task 2: Authentication + Full Input Validation
Covers: register, login, JWT protection, and all validation edge cases.
"""


# ── Register ───────────────────────────────────────────────────────────────────

def test_register_success(client):
    resp = client.post("/auth/register", json={
        "username": "newuser", "email": "new@test.com", "password": "pass123"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newuser"
    assert data["role"] == "reader"
    assert "hashed_password" not in data


def test_register_duplicate_username(client):
    payload = {"username": "dupuser", "email": "dup@test.com", "password": "pass123"}
    client.post("/auth/register", json=payload)
    resp = client.post("/auth/register", json={**payload, "email": "other@test.com"})
    assert resp.status_code == 400
    assert "Username already registered" in resp.json()["detail"]


def test_register_duplicate_email(client):
    client.post("/auth/register", json={"username": "user1", "email": "same@test.com", "password": "pass123"})
    resp = client.post("/auth/register", json={"username": "user2", "email": "same@test.com", "password": "pass123"})
    assert resp.status_code == 400
    assert "Email already registered" in resp.json()["detail"]


# ── Validation: Username ───────────────────────────────────────────────────────

def test_register_username_too_short(client):
    resp = client.post("/auth/register", json={
        "username": "ab", "email": "short@test.com", "password": "pass123"
    })
    assert resp.status_code == 422


def test_register_username_invalid_chars(client):
    resp = client.post("/auth/register", json={
        "username": "hello world!", "email": "inv@test.com", "password": "pass123"
    })
    assert resp.status_code == 422


def test_register_username_with_underscore_ok(client):
    resp = client.post("/auth/register", json={
        "username": "hello_world", "email": "us@test.com", "password": "pass123"
    })
    assert resp.status_code == 201


# ── Validation: Password ───────────────────────────────────────────────────────

def test_register_password_too_short(client):
    resp = client.post("/auth/register", json={
        "username": "validuser", "email": "v@test.com", "password": "abc"
    })
    assert resp.status_code == 422


# ── Validation: Email ─────────────────────────────────────────────────────────

def test_register_invalid_email(client):
    resp = client.post("/auth/register", json={
        "username": "emailtest", "email": "not-an-email", "password": "pass123"
    })
    assert resp.status_code == 422


# ── Validation: Admin role blocked ────────────────────────────────────────────

def test_register_cannot_be_admin(client):
    resp = client.post("/auth/register", json={
        "username": "tryadmin", "email": "adm@test.com", "password": "pass123", "role": "admin"
    })
    assert resp.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_success(client):
    client.post("/auth/register", json={"username": "loginuser", "email": "login@test.com", "password": "mypass123"})
    resp = client.post("/auth/login", data={"username": "loginuser", "password": "mypass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert resp.json()["token_type"] == "bearer"


def test_login_wrong_password(client):
    client.post("/auth/register", json={"username": "wrongpass", "email": "wp@test.com", "password": "correct123"})
    resp = client.post("/auth/login", data={"username": "wrongpass", "password": "wrong"})
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = client.post("/auth/login", data={"username": "ghost", "password": "pass"})
    assert resp.status_code == 401


# ── Protected Endpoints ───────────────────────────────────────────────────────

def test_get_my_profile(client, reader_token):
    resp = client.get("/users/me", headers={"Authorization": f"Bearer {reader_token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "readeruser"


def test_get_my_profile_unauthorized(client):
    resp = client.get("/users/me")
    assert resp.status_code == 401


def test_invalid_token(client):
    resp = client.get("/users/me", headers={"Authorization": "Bearer invalidtoken"})
    assert resp.status_code == 401


def test_expired_malformed_token(client):
    resp = client.get("/users/me", headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.bad.sig"})
    assert resp.status_code == 401


# ── Role-based access ─────────────────────────────────────────────────────────

def test_reader_cannot_create_post(client, reader_token):
    resp = client.post("/posts/", json={"title": "My Post Title Here", "content": "Some long content here to satisfy min length."},
                       headers={"Authorization": f"Bearer {reader_token}"})
    assert resp.status_code == 403


def test_author_can_create_post(client, author_token):
    resp = client.post("/posts/", json={"title": "My Post Title Here", "content": "Some long content here."},
                       headers={"Authorization": f"Bearer {author_token}"})
    assert resp.status_code == 201


def test_reader_cannot_list_users(client, reader_token):
    resp = client.get("/users/", headers={"Authorization": f"Bearer {reader_token}"})
    assert resp.status_code == 403


def test_admin_can_list_users(client, admin_token):
    resp = client.get("/users/", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_refresh_token_success(client):
    # 1. Register and login to get tokens
    client.post("/auth/register", json={"username": "refreshuser", "email": "ref@test.com", "password": "pass123"})
    login_resp = client.post("/auth/login", data={"username": "refreshuser", "password": "pass123"})
    tokens = login_resp.json()
    refresh_token = tokens["refresh_token"]

    # 2. Use refresh token to get a new access token
    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["refresh_token"] == refresh_token
