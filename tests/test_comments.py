def _create_post(client, token):
    return client.post(
        "/posts/",
        json={"title": "Test Post Title", "content": "Content that is long enough to pass validation."},
        headers={"Authorization": f"Bearer {token}"},
    ).json()["id"]


def test_create_comment_as_reader(client, author_token, reader_token):
    post_id = _create_post(client, author_token)
    resp = client.post(
        f"/posts/{post_id}/comments/",
        json={"content": "Nice post!"},
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["content"] == "Nice post!"
    assert resp.json()["parent_id"] is None


def test_create_nested_comment(client, author_token, reader_token):
    post_id = _create_post(client, author_token)
    parent = client.post(
        f"/posts/{post_id}/comments/",
        json={"content": "Top-level comment here!"},
        headers={"Authorization": f"Bearer {reader_token}"},
    ).json()
    resp = client.post(
        f"/posts/{post_id}/comments/",
        json={"content": "Reply here!", "parent_id": parent["id"]},
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["parent_id"] == parent["id"]


def test_list_comments_nested(client, author_token, reader_token):
    post_id = _create_post(client, author_token)
    parent_id = client.post(
        f"/posts/{post_id}/comments/",
        json={"content": "Parent comment here!"},
        headers={"Authorization": f"Bearer {reader_token}"},
    ).json()["id"]
    client.post(
        f"/posts/{post_id}/comments/",
        json={"content": "Child comment reply!", "parent_id": parent_id},
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    resp = client.get(f"/posts/{post_id}/comments/")
    data = resp.json()
    assert data["total"] == 1  # 1 top-level
    assert len(data["items"][0]["replies"]) == 1
    assert data["items"][0]["replies"][0]["content"] == "Child comment reply!"


def test_comment_on_nonexistent_post(client, reader_token):
    resp = client.post(
        "/posts/9999/comments/",
        json={"content": "Ghost comment here!"},
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert resp.status_code == 404


def test_update_own_comment(client, author_token, reader_token):
    post_id = _create_post(client, author_token)
    comment_id = client.post(
        f"/posts/{post_id}/comments/",
        json={"content": "Old comment content"},
        headers={"Authorization": f"Bearer {reader_token}"},
    ).json()["id"]
    resp = client.put(
        f"/posts/{post_id}/comments/{comment_id}",
        json={"content": "Updated comment content"},
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == "Updated comment content"


def test_delete_comment_by_admin(client, author_token, reader_token, admin_token):
    post_id = _create_post(client, author_token)
    comment_id = client.post(
        f"/posts/{post_id}/comments/",
        json={"content": "Please delete me!"},
        headers={"Authorization": f"Bearer {reader_token}"},
    ).json()["id"]
    resp = client.delete(
        f"/posts/{post_id}/comments/{comment_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204


def test_delete_comment_by_other_user_forbidden(client, author_token, reader_token):
    post_id = _create_post(client, author_token)
    comment_id = client.post(
        f"/posts/{post_id}/comments/",
        json={"content": "This is my comment!"},
        headers={"Authorization": f"Bearer {reader_token}"},
    ).json()["id"]
    resp = client.delete(
        f"/posts/{post_id}/comments/{comment_id}",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert resp.status_code == 403
