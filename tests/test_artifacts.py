from pathlib import Path
import os
import time
from uuid import uuid4
from zipfile import ZipFile

from pytest import raises

from app.services.artifacts import (
    ArtifactNotFoundError,
    ArtifactStore,
    ArtifactStoreError,
)


def test_store_lists_only_allow_listed_files(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "runs")
    run_id = uuid4()
    run_dir = store.prepare_run(run_id)
    (run_dir / "agg").mkdir()
    (run_dir / "agg" / "best_config_topn.csv").write_text("csv", encoding="utf-8")
    (run_dir / "agg" / "run_0.sh").write_text("echo test", encoding="utf-8")
    (run_dir / "agg" / "secret.txt").write_text("secret", encoding="utf-8")

    assert store.list_allowed(run_id) == [
        "agg/best_config_topn.csv",
        "agg/run_0.sh",
    ]


def test_store_rejects_traversal_and_unknown_files(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "runs")
    run_id = uuid4()
    run_dir = store.prepare_run(run_id)
    (run_dir / "agg").mkdir()
    (run_dir / "agg" / "best_config_topn.csv").write_text("csv", encoding="utf-8")

    assert store.resolve_allowed(run_id, "agg/best_config_topn.csv").read_text() == "csv"
    for name in ("../secret.txt", "agg/../secret.txt", "agg/secret.txt", "agg\\best_config_topn.csv"):
        with raises(ArtifactNotFoundError):
            store.resolve_allowed(run_id, name)

    outside = tmp_path / "outside.csv"
    outside.write_text("private", encoding="utf-8")
    (run_dir / "agg" / "pareto.csv").symlink_to(outside)
    with raises(ArtifactNotFoundError):
        store.resolve_allowed(run_id, "agg/pareto.csv")


def test_store_finds_one_result_root(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "runs")
    run_id = uuid4()
    run_dir = store.prepare_run(run_id)
    for mode in ("agg", "disagg"):
        mode_dir = run_dir / "Qwen" / "generated" / mode
        mode_dir.mkdir(parents=True)
        (mode_dir / "best_config_topn.csv").write_text("csv", encoding="utf-8")

    assert store.find_result_root(run_id) == run_dir / "Qwen" / "generated"


def test_store_cleans_expired_uuid_run_directories(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "runs", ttl_seconds=60)
    expired_id = uuid4()
    expired_dir = store.prepare_run(expired_id)
    current = time.time()
    old_time = current - 61
    os.utime(expired_dir, (old_time, old_time))

    store.cleanup_expired(now=current)

    assert not expired_dir.exists()


def test_store_creates_bundle_with_relative_paths_and_duplicate_basenames(
    tmp_path: Path,
) -> None:
    store = ArtifactStore(tmp_path / "runs")
    run_id = uuid4()
    run_dir = store.prepare_run(run_id)
    artifact_names = [
        "agg/top1/k8s_deploy.yaml",
        "disagg/top1/k8s_deploy.yaml",
    ]
    for name, content in zip(artifact_names, ("agg", "disagg"), strict=True):
        path = run_dir / name
        path.parent.mkdir(parents=True)
        path.write_text(content, encoding="utf-8")
    (run_dir / "agg" / "secret.txt").write_text("secret", encoding="utf-8")

    bundle_path = store.create_bundle(run_id, artifact_names)

    with ZipFile(bundle_path) as archive:
        assert archive.namelist() == artifact_names
        assert archive.read(artifact_names[0]) == b"agg"
        assert archive.read(artifact_names[1]) == b"disagg"
        assert "agg/secret.txt" not in archive.namelist()


def test_store_rejects_incomplete_or_unsafe_bundle_artifact_sets(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "runs")
    run_id = uuid4()
    run_dir = store.prepare_run(run_id)
    safe_path = run_dir / "agg" / "k8s_deploy.yaml"
    safe_path.parent.mkdir(parents=True)
    safe_path.write_text("safe", encoding="utf-8")

    with raises(ArtifactNotFoundError):
        store.create_bundle(
            run_id,
            ["agg/k8s_deploy.yaml", "disagg/top1/k8s_deploy.yaml"],
        )

    symlink_run_id = uuid4()
    symlink_run_dir = store.prepare_run(symlink_run_id)
    outside = tmp_path / "outside.yaml"
    outside.write_text("private", encoding="utf-8")
    symlink = symlink_run_dir / "disagg" / "top1" / "k8s_deploy.yaml"
    symlink.parent.mkdir(parents=True)
    symlink.symlink_to(outside)
    with raises(ArtifactNotFoundError):
        store.create_bundle(
            symlink_run_id,
            ["disagg/top1/k8s_deploy.yaml"],
        )


def test_store_reports_temporary_bundle_creation_failure(
    tmp_path: Path, monkeypatch
) -> None:
    store = ArtifactStore(tmp_path / "runs")
    run_id = uuid4()
    artifact = store.prepare_run(run_id) / "agg" / "k8s_deploy.yaml"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("safe", encoding="utf-8")

    def fail_temporary_file(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(
        "app.services.artifacts.tempfile.NamedTemporaryFile",
        fail_temporary_file,
    )

    with raises(ArtifactStoreError, match="Could not create artifact bundle"):
        store.create_bundle(run_id, ["agg/k8s_deploy.yaml"])
