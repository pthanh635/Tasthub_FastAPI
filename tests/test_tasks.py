from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_task_crud() -> None:
    created = client.post("/api/v1/tasks", json={"title": "Learn FastAPI"})
    assert created.status_code == 201
    task_id = created.json()["id"]
    assert created.json()["status"] == "TODO"

    fetched = client.get(f"/api/v1/tasks/{task_id}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Learn FastAPI"

    changed = client.put(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Learn Router", "status": "IN_PROGRESS"},
    )
    assert changed.status_code == 200
    assert changed.json()["title"] == "Learn Router"

    deleted = client.delete(f"/api/v1/tasks/{task_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/tasks/{task_id}").status_code == 404


def test_invalid_title() -> None:
    response = client.post("/api/v1/tasks", json={"title": ""})
    assert response.status_code == 422
