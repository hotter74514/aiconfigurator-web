from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.runs import RunRequest
from app.main import create_app
from app.services.executor import ExecutionResult
from app.services.submissions import RunManager


def test_completed_run_can_download_an_allow_listed_artifact(tmp_path: Path) -> None:
    service = RunManager(start_workers=False, artifact_root=tmp_path / "runs")
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
    artifact.parent.mkdir()
    artifact.write_text("apiVersion: apps/v1\n", encoding="utf-8")
    service.mark_completed(
        run.id,
        execution=ExecutionResult(0, "", "", 1),
        artifacts=["agg/k8s_deploy.yaml"],
    )

    client = TestClient(create_app(service))
    response = client.get(f"/api/runs/{run.id}/artifacts/agg/k8s_deploy.yaml")

    assert response.status_code == 200
    assert response.text == "apiVersion: apps/v1\n"


def test_artifact_download_rejects_unknown_and_traversal_paths(tmp_path: Path) -> None:
    service = RunManager(start_workers=False, artifact_root=tmp_path / "runs")
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
    service.mark_completed(
        run.id,
        execution=ExecutionResult(0, "", "", 1),
        artifacts=[],
    )
    client = TestClient(create_app(service))

    assert client.get(f"/api/runs/{run.id}/artifacts/secret.txt").status_code == 404
    assert client.get(f"/api/runs/{run.id}/artifacts/../secret.txt").status_code in {404, 405}
