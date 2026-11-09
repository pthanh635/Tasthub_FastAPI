from httpx import AsyncClient


async def _register_and_login(
    client: AsyncClient,
    *,
    email: str,
    full_name: str,
    password: str = "SecurePass123!",
) -> tuple[str, dict[str, str]]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert reg.status_code == 201
    user_id: str = reg.json()["id"]

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    token: str = login.json()["access_token"]
    return user_id, {"Authorization": f"Bearer {token}"}


async def test_workspace_project_and_task_rbac_and_ownership(
    async_client: AsyncClient,
) -> None:
    """Verify RBAC (OWNER, ADMIN, EDITOR, VIEWER, non-member) and Resource Ownership."""
    owner_id, owner_headers = await _register_and_login(
        async_client,
        email="owner@company.com",
        full_name="Workspace Owner",
    )
    editor_a_id, editor_a_headers = await _register_and_login(
        async_client,
        email="editor_a@company.com",
        full_name="Editor A",
    )
    editor_b_id, editor_b_headers = await _register_and_login(
        async_client,
        email="editor_b@company.com",
        full_name="Editor B",
    )
    viewer_id, viewer_headers = await _register_and_login(
        async_client,
        email="viewer@company.com",
        full_name="Workspace Viewer",
    )
    _outsider_id, outsider_headers = await _register_and_login(
        async_client,
        email="outsider@company.com",
        full_name="Outsider User",
    )

    ws_resp = await async_client.post(
        "/api/v1/workspaces",
        json={"name": "Engineering", "description": "Core Engineering Workspace"},
        headers=owner_headers,
    )
    assert ws_resp.status_code == 201
    ws_id = ws_resp.json()["id"]
    assert ws_resp.json()["owner_id"] == owner_id

    for uid, role in [
        (editor_a_id, "EDITOR"),
        (editor_b_id, "EDITOR"),
        (viewer_id, "VIEWER"),
    ]:
        invite = await async_client.post(
            f"/api/v1/workspaces/{ws_id}/members",
            json={"user_id": uid, "role": role},
            headers=owner_headers,
        )
        assert invite.status_code == 201
        assert invite.json()["role"] == role

    editor_update_ws = await async_client.patch(
        f"/api/v1/workspaces/{ws_id}",
        json={"name": "Hijacked Name"},
        headers=editor_a_headers,
    )
    assert editor_update_ws.status_code == 403

    owner_update_ws = await async_client.patch(
        f"/api/v1/workspaces/{ws_id}",
        json={"name": "Engineering Team"},
        headers=owner_headers,
    )
    assert owner_update_ws.status_code == 200
    assert owner_update_ws.json()["name"] == "Engineering Team"

    viewer_invite = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"user_id": editor_b_id, "role": "ADMIN"},
        headers=viewer_headers,
    )
    assert viewer_invite.status_code == 403

    remove_owner = await async_client.delete(
        f"/api/v1/workspaces/{ws_id}/members/{owner_id}",
        headers=owner_headers,
    )
    assert remove_owner.status_code == 409

    viewer_create_proj = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "Forbidden Project"},
        headers=viewer_headers,
    )
    assert viewer_create_proj.status_code == 403

    proj_resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "Platform API", "description": "FastAPI Backend"},
        headers=editor_a_headers,
    )
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]
    assert proj_resp.json()["status"] == "ACTIVE"

    outsider_get_ws = await async_client.get(
        f"/api/v1/workspaces/{ws_id}",
        headers=outsider_headers,
    )
    assert outsider_get_ws.status_code == 403

    viewer_create_task = await async_client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={"title": "Viewer cannot create task"},
        headers=viewer_headers,
    )
    assert viewer_create_task.status_code == 403

    task_resp = await async_client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={
            "title": "Implement RBAC",
            "description": "Created by Editor A",
            "priority": "HIGH",
            "assignee_id": viewer_id,
        },
        headers=editor_a_headers,
    )
    assert task_resp.status_code == 201
    task_id = task_resp.json()["id"]
    assert task_resp.json()["created_by_id"] == editor_a_id
    assert task_resp.json()["assignee_id"] == viewer_id

    viewer_get_task = await async_client.get(
        f"/api/v1/tasks/{task_id}",
        headers=viewer_headers,
    )
    assert viewer_get_task.status_code == 200

    viewer_patch_task = await async_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"status": "IN_PROGRESS"},
        headers=viewer_headers,
    )
    assert viewer_patch_task.status_code == 403

    editor_b_patch_task = await async_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"status": "IN_PROGRESS"},
        headers=editor_b_headers,
    )
    assert editor_b_patch_task.status_code == 200
    assert editor_b_patch_task.json()["status"] == "IN_PROGRESS"

    editor_b_delete_task = await async_client.delete(
        f"/api/v1/tasks/{task_id}",
        headers=editor_b_headers,
    )
    assert editor_b_delete_task.status_code == 403

    editor_a_delete_task = await async_client.delete(
        f"/api/v1/tasks/{task_id}",
        headers=editor_a_headers,
    )
    assert editor_a_delete_task.status_code == 204

    archive_proj = await async_client.patch(
        f"/api/v1/projects/{proj_id}",
        json={"status": "ARCHIVED"},
        headers=owner_headers,
    )
    assert archive_proj.status_code == 200
    assert archive_proj.json()["status"] == "ARCHIVED"

    task_in_archived = await async_client.post(
        f"/api/v1/projects/{proj_id}/tasks",
        json={"title": "Cannot create in archived project"},
        headers=owner_headers,
    )
    assert task_in_archived.status_code == 400

