# Blog Management System

> A production-ready blog API built with **FastAPI** — featuring JWT authentication, role-based access control, nested comments, an admin dashboard, and a vanilla JS frontend.

---

## Preview

```
http://localhost:8000/frontend   →  Frontend UI
http://localhost:8000/docs       →  Swagger API Docs
```

---

## Tech Stack

- **FastAPI** — modern, high-performance Python web framework
- **SQLAlchemy + SQLite** — ORM and database
- **Pydantic v2** — request validation and serialization
- **python-jose + passlib** — JWT tokens and password hashing
- **pytest + TestClient** — 26 automated tests
- **Docker + docker-compose** — containerized deployment
- **Vanilla JS / HTML / CSS** — lightweight frontend, no frameworks

---

## Getting Started

### Prerequisites
- Python 3.11+

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/your-username/blog-management-system.git
cd blog-management-system

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
uvicorn app.main:app --reload
```

### Or with Docker

```bash
docker-compose up --build
```

The app will be running at `http://localhost:8000`

---

## Default Admin

A default admin account is created automatically on first run:

```
Username: admin
Password: admin123
```

> ⚠️ Change the password in production.

---

## Roles & Permissions

| Permission | Reader | Author | Admin |
|---|:---:|:---:|:---:|
| Read posts | ✅ | ✅ | ✅ |
| Leave comments | ✅ | ✅ | ✅ |
| Reply to comments | ✅ | ✅ | ✅ |
| Create posts | ❌ | ✅ | ✅ |
| Edit own posts | ❌ | ✅ | ✅ |
| Delete any post | ❌ | ❌ | ✅ |
| Delete any comment | ❌ | ❌ | ✅ |
| Manage users & roles | ❌ | ❌ | ✅ |

> Users self-register as **Reader** or **Author**. Only the Admin can promote or delete accounts.

---

## API Reference

### Authentication
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/auth/register` | Public | Register as Reader or Author |
| `POST` | `/auth/login` | Public | Login and receive JWT token |

### Posts
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/posts/` | Public | List all posts (paginated) |
| `GET` | `/posts/{id}` | Public | Get single post with full content |
| `POST` | `/posts/` | Author, Admin | Create a new post |
| `PUT` | `/posts/{id}` | Owner, Admin | Update a post |
| `DELETE` | `/posts/{id}` | Admin | Delete a post |

### Comments
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/posts/{id}/comments/` | Public | List comments as nested tree |
| `POST` | `/posts/{id}/comments/` | Authenticated | Add comment or reply |
| `PUT` | `/posts/{id}/comments/{cid}` | Owner, Admin | Edit a comment |
| `DELETE` | `/posts/{id}/comments/{cid}` | Owner, Admin | Delete a comment |

### Users
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/users/me` | Authenticated | Get own profile |
| `PUT` | `/users/me` | Authenticated | Update own profile |
| `GET` | `/users/` | Admin | List all users |
| `GET` | `/users/{id}` | Admin | Get user by ID |
| `PUT` | `/users/{id}` | Admin | Update user role or status |
| `DELETE` | `/users/{id}` | Admin | Delete a user |

---

## Project Structure

```
blog_final/
├── app/
│   ├── main.py              # App entry point + auto admin creation
│   ├── database.py          # SQLAlchemy engine and session
│   ├── core/
│   │   ├── config.py        # Environment settings
│   │   ├── security.py      # JWT creation and password hashing
│   │   └── dependencies.py  # Auth dependencies and role guards
│   ├── models/
│   │   ├── user.py          # User model with roles enum
│   │   ├── post.py          # Post model
│   │   └── comment.py       # Comment model with self-referential FK
│   ├── schemas/
│   │   ├── user.py          # User request/response schemas
│   │   ├── post.py          # Post schemas with pagination
│   │   └── comment.py       # Comment schemas with nested replies
│   ├── routes/
│   │   ├── auth.py          # Register and login endpoints
│   │   ├── users.py         # User management endpoints
│   │   ├── posts.py         # Post CRUD endpoints
│   │   └── comments.py      # Comment CRUD endpoints
│   └── services/
│       ├── auth_service.py  # Registration and login logic
│       ├── post_service.py  # Post business logic
│       └── comment_service.py # Comment + nested tree logic
├── frontend/
│   └── index.html           # Single-page vanilla JS frontend
├── tests/
│   ├── conftest.py          # Fixtures and test DB setup
│   ├── test_auth.py         # Authentication tests
│   ├── test_posts.py        # Post CRUD and permission tests
│   └── test_comments.py     # Comment and nested reply tests
├── Dockerfile
├── docker-compose.yaml
└── requirements.txt
```

---

## Running Tests

```bash
python -m pytest tests/ -v
```

```
26 passed ✅
```

---

## Environment Variables

Create a `.env` file in the root directory to override defaults:

```env
SECRET_KEY=your-super-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=sqlite:///./blog.db
```

