from pathlib import Path
import os
import time
from uuid import uuid4

from pytest import raises

from app.services.artifacts import ArtifactNotFoundError, ArtifactStore


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
