from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.domain.runs import RunRequest
from app.main import create_app
from app.services.artifacts import ArtifactStoreError
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


def test_completed_run_can_download_all_artifacts_as_one_zip(tmp_path: Path) -> None:
    artifact_root = tmp_path / "runs"
    service = RunManager(start_workers=False, artifact_root=artifact_root)
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
    artifact_names = [
        "agg/top1/k8s_deploy.yaml",
        "disagg/top1/k8s_deploy.yaml",
    ]
    for name, content in zip(artifact_names, ("agg", "disagg"), strict=True):
        artifact = service.artifact_dir(run.id) / name
        artifact.parent.mkdir(parents=True)
        artifact.write_text(content, encoding="utf-8")
    service.mark_completed(
        run.id,
        execution=ExecutionResult(0, "", "", 1),
        artifacts=artifact_names,
    )

    client = TestClient(create_app(service))
    response = client.get(f"/api/runs/{run.id}/artifacts.zip")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert (
        response.headers["content-disposition"]
        == f'attachment; filename="aiconfigurator-run-{run.id}-artifacts.zip"'
    )
    with ZipFile(BytesIO(response.content)) as archive:
        assert archive.namelist() == artifact_names
        assert archive.read(artifact_names[0]) == b"agg"
        assert archive.read(artifact_names[1]) == b"disagg"
    assert list(artifact_root.glob("*.zip")) == []


def test_bundle_rejects_nonterminal_empty_and_incomplete_runs(tmp_path: Path) -> None:
    service = RunManager(start_workers=False, artifact_root=tmp_path / "runs")
    request = RunRequest(
        model="Qwen/Qwen3-32B-FP8",
        system="h200_sxm",
        total_gpus=32,
        ttft=2000,
        tpot=30,
    )
    queued = service.submit(request)
    empty = service.submit(request)
    service.mark_running(empty.id)
    service.mark_completed(
        empty.id,
        execution=ExecutionResult(0, "", "", 1),
        artifacts=[],
    )
    incomplete = service.submit(request)
    service.mark_running(incomplete.id)
    artifact = service.artifact_dir(incomplete.id) / "agg" / "k8s_deploy.yaml"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("present", encoding="utf-8")
    service.mark_completed(
        incomplete.id,
        execution=ExecutionResult(0, "", "", 1),
        artifacts=["agg/k8s_deploy.yaml", "disagg/top1/k8s_deploy.yaml"],
    )
    failed = service.submit(request)
    service.mark_running(failed.id)
    service.mark_failed(failed.id, "AIConfigurator failed")
    client = TestClient(create_app(service))

    assert client.get(f"/api/runs/{queued.id}/artifacts.zip").status_code == 404
    assert client.get(f"/api/runs/{empty.id}/artifacts.zip").status_code == 404
    assert client.get(f"/api/runs/{incomplete.id}/artifacts.zip").status_code == 404
    assert client.get(f"/api/runs/{failed.id}/artifacts.zip").status_code == 404


def test_bundle_reports_transient_archive_creation_failure(
    tmp_path: Path, monkeypatch
) -> None:
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
    artifact.parent.mkdir(parents=True)
    artifact.write_text("present", encoding="utf-8")
    service.mark_completed(
        run.id,
        execution=ExecutionResult(0, "", "", 1),
        artifacts=["agg/k8s_deploy.yaml"],
    )

    def fail_bundle(*_args, **_kwargs):
        raise ArtifactStoreError("disk full")

    monkeypatch.setattr(service._artifacts, "create_bundle", fail_bundle)
    response = TestClient(create_app(service)).get(
        f"/api/runs/{run.id}/artifacts.zip"
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Artifact bundle could not be created"}
