import uuid

from httpx import AsyncClient

from app.core.seed import SeedContext


async def test_health(async_client: AsyncClient) -> None:
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_swagger_ui_and_openapi_schema(async_client: AsyncClient) -> None:
    docs_response = await async_client.get("/docs")
    assert docs_response.status_code == 200
    assert "Swagger UI" in docs_response.text

    openapi_response = await async_client.get("/openapi.json")
    assert openapi_response.status_code == 200
    schema = openapi_response.json()
    assert "/api/v1/tasks" in schema["paths"]
    assert "/api/v1/tasks/{task_id}" in schema["paths"]


async def test_task_crud(
    async_client: AsyncClient,
    seed_context: SeedContext,
) -> None:
    create_payload = {
        "project_id": str(seed_context.project_id),
        "title": "Learn FastAPI & SQLAlchemy 2.x",
        "description": "Migrate Task CRUD to PostgreSQL",
        "status": "TODO",
        "priority": "HIGH",
        "assignee_id": str(seed_context.user_id),
        "due_date": "2026-11-15T10:00:00Z",
    }
    created = await async_client.post("/api/v1/tasks", json=create_payload)
    assert created.status_code == 201
    body = created.json()
    task_id = body["id"]
    assert body["project_id"] == str(seed_context.project_id)
    assert body["created_by_id"] == str(seed_context.user_id)
    assert body["assignee_id"] == str(seed_context.user_id)
    assert body["status"] == "TODO"
    assert body["priority"] == "HIGH"
    assert "created_at" in body
    assert "updated_at" in body

    listed = await async_client.get("/api/v1/tasks?offset=0&limit=10")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == task_id

    fetched = await async_client.get(f"/api/v1/tasks/{task_id}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Learn FastAPI & SQLAlchemy 2.x"

    changed = await async_client.put(
        f"/api/v1/tasks/{task_id}",
        json={
            "title": "Learn Repository Pattern",
            "description": "Completed Day 2",
            "status": "IN_PROGRESS",
            "priority": "URGENT",
            "assignee_id": None,
            "due_date": None,
        },
    )
    assert changed.status_code == 200
    assert changed.json()["title"] == "Learn Repository Pattern"
    assert changed.json()["status"] == "IN_PROGRESS"
    assert changed.json()["priority"] == "URGENT"
    assert changed.json()["assignee_id"] is None

    deleted = await async_client.delete(f"/api/v1/tasks/{task_id}")
    assert deleted.status_code == 204

    not_found = await async_client.get(f"/api/v1/tasks/{task_id}")
    assert not_found.status_code == 404


async def test_task_not_found_endpoints(
    async_client: AsyncClient,
    seed_context: SeedContext,
) -> None:
    missing_id = uuid.uuid4()

    get_resp = await async_client.get(f"/api/v1/tasks/{missing_id}")
    assert get_resp.status_code == 404

    put_resp = await async_client.put(
        f"/api/v1/tasks/{missing_id}",
        json={"title": "Non-existent task"},
    )
    assert put_resp.status_code == 404

    del_resp = await async_client.delete(f"/api/v1/tasks/{missing_id}")
    assert del_resp.status_code == 404

    bad_project_resp = await async_client.post(
        "/api/v1/tasks",
        json={"project_id": str(uuid.uuid4()), "title": "Orphan task"},
    )
    assert bad_project_resp.status_code == 404

    bad_assignee_resp = await async_client.post(
        "/api/v1/tasks",
        json={
            "project_id": str(seed_context.project_id),
            "title": "Unknown assignee",
            "assignee_id": str(uuid.uuid4()),
        },
    )
    assert bad_assignee_resp.status_code == 404


async def test_input_validation_errors(
    async_client: AsyncClient,
    seed_context: SeedContext,
) -> None:
    empty_title = await async_client.post(
        "/api/v1/tasks",
        json={"project_id": str(seed_context.project_id), "title": ""},
    )
    assert empty_title.status_code == 422

    missing_project = await async_client.post(
        "/api/v1/tasks",
        json={"title": "Missing project_id"},
    )
    assert missing_project.status_code == 422

    invalid_status = await async_client.post(
        "/api/v1/tasks",
        json={
            "project_id": str(seed_context.project_id),
            "title": "Invalid enum",
            "status": "INVALID_STATUS",
        },
    )
    assert invalid_status.status_code == 422

    invalid_uuid = await async_client.get("/api/v1/tasks/not-a-uuid")
    assert invalid_uuid.status_code == 422

    invalid_pagination = await async_client.get("/api/v1/tasks?offset=-1&limit=500")
    assert invalid_pagination.status_code == 422
