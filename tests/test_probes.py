from pathlib import Path
from threading import Event

from fastapi.testclient import TestClient

from app.domain.runs import RunRequest
from app.main import create_app
from app.services.executor import ExecutionResult
from app.services.submissions import RunManager


def make_request() -> RunRequest:
    return RunRequest(
        model="Qwen/Qwen3-32B-FP8",
        system="h200_sxm",
        total_gpus=32,
        ttft=2000,
        tpot=30,
    )


def test_live_and_ready_are_healthy_for_initialized_service(tmp_path: Path) -> None:
    service = RunManager(artifact_root=tmp_path / "runs")
    try:
        client = TestClient(create_app(service))

        assert client.get("/live").json() == {"status": "ok"}
        ready = client.get("/ready")
        assert ready.status_code == 200
        assert ready.json() == {"status": "ready"}
    finally:
        service.shutdown()


def test_ready_fails_when_workers_are_not_initialized(tmp_path: Path) -> None:
    service = RunManager(start_workers=False, artifact_root=tmp_path / "runs")
    client = TestClient(create_app(service))

    assert client.get("/live").status_code == 200
    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Worker initialization is incomplete"}


def test_ready_fails_when_artifact_storage_is_not_writable(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifact-root"
    artifact_root.write_text("not a directory", encoding="utf-8")
    service = RunManager(artifact_root=artifact_root)
    try:
        response = TestClient(create_app(service)).get("/ready")
    finally:
        service.shutdown()

    assert response.status_code == 503
    assert response.json() == {"detail": "Artifact storage is not writable"}


def test_ready_stays_healthy_while_worker_is_busy(tmp_path: Path) -> None:
    started = Event()
    release = Event()

    def blocking_runner(
        _: RunRequest, save_dir: Path, cancel_event: Event
    ) -> ExecutionResult:
        del save_dir, cancel_event
        started.set()
        release.wait(timeout=2)
        return ExecutionResult(7, "", "busy test", 1)

    service = RunManager(
        runner=blocking_runner,
        artifact_root=tmp_path / "runs",
    )
    try:
        service.submit(make_request())
        assert started.wait(timeout=2)
        response = TestClient(create_app(service)).get("/ready")
    finally:
        release.set()
        service.shutdown()

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_live_stays_healthy_after_manager_shutdown(tmp_path: Path) -> None:
    service = RunManager(start_workers=False, artifact_root=tmp_path / "runs")
    service.shutdown()
    client = TestClient(create_app(service))

    assert client.get("/live").status_code == 200
    ready = client.get("/ready")
    assert ready.status_code == 503
    assert ready.json() == {"detail": "Run manager is shutting down"}
