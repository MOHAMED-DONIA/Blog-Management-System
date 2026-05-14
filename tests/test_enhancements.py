"""
Tests for Task 7: Enhancements — Caching + Monitoring
"""


# ── Cache: Posts ──────────────────────────────────────────────────────────────

def test_posts_cache_hit_on_second_request(client, author_token):
    """Second identical request should be served from cache (smoke test)."""
    # Create a post first
    client.post("/posts/", json={"title": "Cache Test Post", "content": "This content is long enough to pass validation."},
                headers={"Authorization": f"Bearer {author_token}"})

    r1 = client.get("/posts/?page=1&size=10")
    r2 = client.get("/posts/?page=1&size=10")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["total"] == r2.json()["total"]


def test_cache_invalidated_after_new_post(client, author_token):
    """Creating a new post should bust the list cache."""
    # Prime the cache
    r1 = client.get("/posts/?page=1&size=10")
    initial_total = r1.json()["total"]

    # Create a new post (this must invalidate the list cache)
    client.post(
        "/posts/",
        json={"title": "Brand New Post Title", "content": "Content that is definitely long enough here."},
        headers={"Authorization": f"Bearer {author_token}"},
    )

    # The next GET must reflect the new post, not serve stale cache
    r2 = client.get("/posts/?page=1&size=10")
    assert r2.json()["total"] == initial_total + 1


def test_cache_invalidated_after_delete(client, author_token, admin_token):
    """Deleting a post should invalidate the cache."""
    r_create = client.post("/posts/", json={"title": "Post To Delete Cache", "content": "Content that is definitely long enough."},
                           headers={"Authorization": f"Bearer {author_token}"})
    post_id = r_create.json()["id"]

    r1 = client.get("/posts/?page=1&size=10")
    before_count = r1.json()["total"]

    client.delete(f"/posts/{post_id}", headers={"Authorization": f"Bearer {admin_token}"})

    r2 = client.get("/posts/?page=1&size=10")
    assert r2.json()["total"] == before_count - 1


# ── Monitoring Endpoints ───────────────────────────────────────────────────────

def test_metrics_requires_admin(client, reader_token):
    resp = client.get("/metrics/", headers={"Authorization": f"Bearer {reader_token}"})
    assert resp.status_code == 403


def test_metrics_unauthenticated(client):
    resp = client.get("/metrics/")
    assert resp.status_code == 401


def test_metrics_returns_snapshot(client, admin_token):
    resp = client.get("/metrics/", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "requests" in data
    assert "uptime" in data
    assert "operations" in data
    assert "performance" in data


def test_metrics_tracks_requests(client, admin_token):
    """Making requests should increment total_requests counter."""
    r1 = client.get("/metrics/", headers={"Authorization": f"Bearer {admin_token}"})
    before = r1.json()["requests"]["total"]

    # Make some requests
    client.get("/posts/")
    client.get("/posts/")
    client.get("/posts/")

    r2 = client.get("/metrics/", headers={"Authorization": f"Bearer {admin_token}"})
    after = r2.json()["requests"]["total"]

    assert after > before


def test_cache_stats_endpoint(client, admin_token):
    resp = client.get("/metrics/cache", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "posts_cache" in data
    assert "comments_cache" in data
    assert "active_keys" in data["posts_cache"]


def test_clear_cache_endpoint(client, admin_token):
    resp = client.delete("/metrics/cache", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "All caches cleared" in data["message"]


# ── Post Validation (Task 2 link) ─────────────────────────────────────────────

def test_post_title_too_short(client, author_token):
    resp = client.post("/posts/", json={"title": "Hi", "content": "Long enough content here."},
                       headers={"Authorization": f"Bearer {author_token}"})
    assert resp.status_code == 422


def test_post_content_too_short(client, author_token):
    resp = client.post("/posts/", json={"title": "Valid Title Here", "content": "Short"},
                       headers={"Authorization": f"Bearer {author_token}"})
    assert resp.status_code == 422


def test_comment_empty_content(client, reader_token, author_token):
    post = client.post("/posts/", json={"title": "Post For Comment Test", "content": "Enough content to be valid."},
                       headers={"Authorization": f"Bearer {author_token}"})
    post_id = post.json()["id"]

    resp = client.post(f"/posts/{post_id}/comments", json={"content": "   "},
                       headers={"Authorization": f"Bearer {reader_token}"})
    assert resp.status_code == 422
