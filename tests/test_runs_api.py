from uuid import UUID

from fastapi.testclient import TestClient
from pytest import raises

from app.domain.runs import RunRequest
from app.main import create_app
from app.services.submissions import RunManager, RunTransitionError


def make_client() -> tuple[TestClient, RunManager]:
    service = RunManager(start_workers=False)
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


def test_post_runs_returns_503_after_shutdown() -> None:
    service = RunManager(start_workers=False)
    service.shutdown()
    client = TestClient(create_app(service))

    response = client.post(
        "/api/runs",
        json={
            "model": "Qwen/Qwen3-32B-FP8",
            "system": "h200_sxm",
            "total_gpus": 32,
            "ttft": 2000,
            "tpot": 30,
        },
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Run manager is shutting down"}


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


def test_get_run_returns_queued_status_after_submission() -> None:
    client, _ = make_client()
    response = client.post(
        "/api/runs",
        json={
            "model": "Qwen/Qwen3-32B-FP8",
            "system": "h200_sxm",
            "total_gpus": 32,
            "ttft": 2000,
            "tpot": 30,
        },
    )
    run_id = response.json()["id"]

    status_response = client.get(f"/api/runs/{run_id}")

    assert status_response.status_code == 200
    assert status_response.json() == {"id": run_id, "status": "queued"}


def test_get_runs_returns_recent_terminal_history_newest_first(tmp_path) -> None:
    service = RunManager(
        start_workers=False,
        artifact_root=tmp_path / "runs",
        history_size=2,
    )
    client = TestClient(create_app(service))
    first = service.submit(
        RunRequest(
            model="first-model",
            system="h200_sxm",
            total_gpus=8,
            ttft=100,
            tpot=10,
        )
    )
    service.mark_running(first.id)
    service.mark_completed(first.id)
    second = service.submit(
        RunRequest(
            model="second-model",
            system="h100_sxm",
            total_gpus=4,
            ttft=200,
            tpot=20,
        )
    )
    service.mark_running(second.id)
    service.mark_failed(second.id, "configuration failed")

    response = client.get("/api/runs")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [
        str(second.id),
        str(first.id),
    ]
    assert response.json()[0]["status"] == "failed"
    assert response.json()[0]["error"] == "configuration failed"
    assert response.json()[0]["request"]["model"] == "second-model"


def test_get_runs_returns_empty_history_without_terminal_runs() -> None:
    client, _ = make_client()

    response = client.get("/api/runs")

    assert response.status_code == 200
    assert response.json() == []


def test_get_runs_marks_expired_artifacts_unavailable(tmp_path) -> None:
    service = RunManager(
        start_workers=False,
        artifact_root=tmp_path / "runs",
    )
    run = service.submit(
        RunRequest(
            model="Qwen/Qwen3-32B-FP8",
            system="h200_sxm",
            total_gpus=32,
            ttft=2000,
            tpot=30,
        )
    )
    service.mark_running(run.id)
    artifact = service.artifact_dir(run.id) / "agg" / "k8s_deploy.yaml"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("apiVersion: apps/v1\n", encoding="utf-8")
    service.mark_completed(
        run.id,
        artifacts=["agg/k8s_deploy.yaml"],
    )
    artifact.unlink()
    client = TestClient(create_app(service))

    response = client.get("/api/runs")

    assert response.status_code == 200
    assert response.json()[0]["artifacts"] == []
    assert response.json()[0]["artifacts_unavailable"] is True


def test_get_run_returns_running_and_completed_transitions() -> None:
    service = RunManager(start_workers=False)
    client = TestClient(create_app(service))
    run = service.submit(
        RunRequest(
            model="Qwen/Qwen3-32B-FP8",
            system="h200_sxm",
            total_gpus=32,
            ttft=2000,
            tpot=30,
        )
    )

    service.mark_running(run.id)
    running_response = client.get(f"/api/runs/{run.id}")
    service.mark_completed(run.id)
    completed_response = client.get(f"/api/runs/{run.id}")

    assert running_response.json() == {"id": str(run.id), "status": "running"}
    assert completed_response.json() == {"id": str(run.id), "status": "completed"}


def test_get_run_returns_safe_failure_detail() -> None:
    service = RunManager(start_workers=False)
    client = TestClient(create_app(service))
    run = service.submit(
        RunRequest(
            model="Qwen/Qwen3-32B-FP8",
            system="h200_sxm",
            total_gpus=32,
            ttft=2000,
            tpot=30,
        )
    )

    service.mark_running(run.id)
    service.mark_failed(run.id, "AIConfigurator exited with status 1")

    response = client.get(f"/api/runs/{run.id}")

    assert response.json() == {
        "id": str(run.id),
        "status": "failed",
        "error": "AIConfigurator exited with status 1",
    }


def test_get_run_returns_not_found_for_unknown_id() -> None:
    client, _ = make_client()

    response = client.get("/api/runs/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json() == {"detail": "Run not found"}


def test_status_transitions_reject_invalid_lifecycle_changes() -> None:
    service = RunManager(start_workers=False)
    run = service.submit(
        RunRequest(
            model="Qwen/Qwen3-32B-FP8",
            system="h200_sxm",
            total_gpus=32,
            ttft=2000,
            tpot=30,
        )
    )

    with raises(RunTransitionError):
        service.mark_completed(run.id)


def test_post_runs_returns_429_when_pending_queue_is_full() -> None:
    service = RunManager(start_workers=False, queue_size=1)
    client = TestClient(create_app(service))
    payload = {
        "model": "Qwen/Qwen3-32B-FP8",
        "system": "h200_sxm",
        "total_gpus": 32,
        "ttft": 2000,
        "tpot": 30,
    }

    first_response = client.post("/api/runs", json=payload)
    second_response = client.post("/api/runs", json=payload)

    assert first_response.status_code == 202
    assert second_response.status_code == 429
    assert second_response.headers["retry-after"] == "1"
    assert second_response.json() == {"detail": "Run queue is full"}
    assert service.count() == 1
