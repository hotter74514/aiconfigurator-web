from uuid import UUID

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.submissions import InMemoryRunSubmissionService


def make_client() -> tuple[TestClient, InMemoryRunSubmissionService]:
    service = InMemoryRunSubmissionService()
    return TestClient(create_app(service)), service


def test_post_runs_returns_queued_run_and_stores_constraints() -> None:
    client, service = make_client()

    response = client.post(
        "/api/runs",
        json={
            "model": " Qwen/Qwen3-32B-FP8 ",
            "system": " h200_sxm ",
            "total_gpus": 32,
            "ttft": 2000,
            "tpot": 30,
        },
    )

    assert response.status_code == 202
    body = response.json()
    run_id = UUID(body["id"])
    assert body == {"id": str(run_id), "status": "queued"}

    stored = service.get(run_id)
    assert stored is not None
    assert stored.request.model == "Qwen/Qwen3-32B-FP8"
    assert stored.request.system == "h200_sxm"
    assert stored.request.total_gpus == 32
    assert stored.request.ttft == 2000
    assert stored.request.tpot == 30


def test_post_runs_rejects_missing_constraints() -> None:
    client, service = make_client()

    response = client.post("/api/runs", json={"model": "Qwen/Qwen3-32B-FP8"})

    assert response.status_code == 422
    assert service.count() == 0


def test_post_runs_rejects_invalid_numeric_constraints() -> None:
    client, service = make_client()

    response = client.post(
        "/api/runs",
        json={
            "model": "Qwen/Qwen3-32B-FP8",
            "system": "h200_sxm",
            "total_gpus": 0,
            "ttft": -1,
            "tpot": 0,
        },
    )

    assert response.status_code == 422
    assert service.count() == 0


def test_post_runs_rejects_unknown_fields() -> None:
    client, service = make_client()

    response = client.post(
        "/api/runs",
        json={
            "model": "Qwen/Qwen3-32B-FP8",
            "system": "h200_sxm",
            "total_gpus": 32,
            "ttft": 2000,
            "tpot": 30,
            "backend": "trtllm",
        },
    )

    assert response.status_code == 422
    assert service.count() == 0


def test_post_runs_rejects_whitespace_only_text() -> None:
    client, service = make_client()

    response = client.post(
        "/api/runs",
        json={
            "model": "   ",
            "system": "h200_sxm",
            "total_gpus": 32,
            "ttft": 2000,
            "tpot": 30,
        },
    )

    assert response.status_code == 422
    assert service.count() == 0
