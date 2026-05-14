def test_list_posts_public(client):
    resp = client.get("/posts/")
    assert resp.status_code == 200
    assert "items" in resp.json()
    assert resp.json()["total"] == 0


def test_create_post_as_author(client, author_token):
    resp = client.post(
        "/posts/",
        json={"title": "My First Post Title", "content": "Hello world, this is enough content!"},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "My First Post Title"
    assert data["author"]["username"] == "authoruser"


def test_create_post_as_reader_forbidden(client, reader_token):
    resp = client.post(
        "/posts/",
        json={"title": "Not allowed post", "content": "Should fail because reader role."},
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert resp.status_code == 403


def test_create_post_unauthenticated(client):
    resp = client.post("/posts/", json={"title": "Nope fail here", "content": "Should fail without token."})
    assert resp.status_code == 401


def test_get_single_post(client, author_token):
    create_resp = client.post(
        "/posts/",
        json={"title": "Single Post Title", "content": "Content that is long enough here."},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    post_id = create_resp.json()["id"]
    resp = client.get(f"/posts/{post_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == post_id


def test_get_nonexistent_post(client):
    resp = client.get("/posts/9999")
    assert resp.status_code == 404


def test_update_own_post(client, author_token):
    post_id = client.post(
        "/posts/",
        json={"title": "Old Post Title", "content": "Old content that is long enough."},
        headers={"Authorization": f"Bearer {author_token}"},
    ).json()["id"]
    resp = client.put(
        f"/posts/{post_id}",
        json={"title": "Brand New Title"},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Brand New Title"


def test_delete_post_as_admin(client, author_token, admin_token):
    post_id = client.post(
        "/posts/",
        json={"title": "Post To Be Deleted", "content": "Goodbye from this post."},
        headers={"Authorization": f"Bearer {author_token}"},
    ).json()["id"]
    resp = client.delete(f"/posts/{post_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 204


def test_delete_post_as_non_admin_forbidden(client, author_token):
    post_id = client.post(
        "/posts/",
        json={"title": "Post That Stays", "content": "Author cannot delete their own post."},
        headers={"Authorization": f"Bearer {author_token}"},
    ).json()["id"]
    resp = client.delete(f"/posts/{post_id}", headers={"Authorization": f"Bearer {author_token}"})
    assert resp.status_code == 403


def test_pagination(client, author_token):
    for i in range(5):
        client.post(
            "/posts/",
            json={"title": f"Paginated Post {i+1}", "content": "Content that is long enough to be valid."},
            headers={"Authorization": f"Bearer {author_token}"},
        )
    resp = client.get("/posts/?page=1&size=3")
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 3
    assert data["pages"] == 2
