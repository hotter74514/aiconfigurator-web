import time
from pathlib import Path
from threading import Event
from uuid import UUID

from pytest import raises

from app.domain.runs import RunRequest
from app.services.executor import ExecutionResult, build_aiconfigurator_command
from app.services.submissions import QueueCapacityError, RunManager


def make_request() -> RunRequest:
    return RunRequest(
        model="Qwen/Qwen3-32B-FP8",
        system="h200_sxm",
        total_gpus=32,
        ttft=2000,
        tpot=30,
    )


def wait_for_status(manager: RunManager, run_id: UUID, expected: str) -> None:
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        run = manager.get(run_id)
        if run is not None and run.status == expected:
            return
        time.sleep(0.01)
    raise AssertionError(f"run did not reach {expected}")


def successful_runner(_: RunRequest, save_dir: Path) -> ExecutionResult:
    result_dir = save_dir / "agg"
    result_dir.mkdir(parents=True)
    (result_dir / "best_config_topn.csv").write_text(
        "model,ttft,tpot,request_latency,tokens/s,tokens/s/gpu,"
        "num_total_gpus,concurrency,backend,system\n"
        "Qwen/Qwen3-32B-FP8,1000,29,30000,1000,1000,1,1,trtllm,h200_sxm\n",
        encoding="utf-8",
    )
    return ExecutionResult(
        exit_code=0,
        stdout="AIConfigurator Final Results",
        stderr="",
        duration_ms=12,
    )


def failing_runner(_: RunRequest, save_dir: Path) -> ExecutionResult:
    del save_dir
    return ExecutionResult(
        exit_code=7,
        stdout="partial output",
        stderr="configuration failed",
        duration_ms=18,
    )


def raising_runner(_: RunRequest, save_dir: Path) -> ExecutionResult:
    del save_dir
    raise RuntimeError("runner crashed")


def test_command_builder_passes_user_constraints() -> None:
    assert build_aiconfigurator_command(make_request()) == [
        "aiconfigurator",
        "cli",
        "default",
        "--model",
        "Qwen/Qwen3-32B-FP8",
        "--total-gpus",
        "32",
        "--system",
        "h200_sxm",
        "--ttft",
        "2000.0",
        "--tpot",
        "30.0",
    ]

    assert build_aiconfigurator_command(
        make_request(), Path("/tmp/run-artifacts")
    )[-2:] == ["--save-dir", "/tmp/run-artifacts"]


def test_worker_marks_success_and_captures_stdout() -> None:
    manager = RunManager(runner=successful_runner)
    try:
        run = manager.submit(make_request())
        wait_for_status(manager, run.id, "completed")
        stored = manager.get(run.id)
    finally:
        manager.shutdown()

    assert stored is not None
    assert stored.stdout == "AIConfigurator Final Results"
    assert stored.stderr == ""
    assert stored.exit_code == 0
    assert stored.duration_ms == 12
    assert stored.error is None
    assert stored.results is not None
    assert stored.results.candidates[0].predicted_tokens_per_second == 1000
    assert stored.artifacts == ["agg/best_config_topn.csv"]


def test_worker_marks_nonzero_exit_as_failed_and_captures_stderr() -> None:
    manager = RunManager(runner=failing_runner)
    try:
        run = manager.submit(make_request())
        wait_for_status(manager, run.id, "failed")
        stored = manager.get(run.id)
    finally:
        manager.shutdown()

    assert stored is not None
    assert stored.error == "AIConfigurator exited with status 7"
    assert stored.stdout == "partial output"
    assert stored.stderr == "configuration failed"
    assert stored.exit_code == 7


def test_worker_captures_runner_exception_as_failed() -> None:
    manager = RunManager(runner=raising_runner)
    try:
        run = manager.submit(make_request())
        wait_for_status(manager, run.id, "failed")
        stored = manager.get(run.id)
    finally:
        manager.shutdown()

    assert stored is not None
    assert stored.error == "Worker execution failed: runner crashed"


def test_pending_queue_rejects_work_after_capacity() -> None:
    manager = RunManager(start_workers=False, queue_size=2)
    manager.submit(make_request())
    manager.submit(make_request())

    with raises(QueueCapacityError):
        manager.submit(make_request())

    assert manager.count() == 2


def test_pending_queue_rejects_work_while_worker_and_queue_are_busy() -> None:
    started = Event()
    release = Event()

    def blocking_runner(_: RunRequest, save_dir: Path) -> ExecutionResult:
        del save_dir
        started.set()
        assert release.wait(timeout=2)
        return ExecutionResult(
            exit_code=7,
            stdout="",
            stderr="capacity test",
            duration_ms=1,
        )

    manager = RunManager(
        runner=blocking_runner,
        worker_count=1,
        queue_size=1,
    )
    try:
        active = manager.submit(make_request())
        assert started.wait(timeout=2)
        queued = manager.submit(make_request())

        with raises(QueueCapacityError):
            manager.submit(make_request())

        active_run = manager.get(active.id)
        queued_run = manager.get(queued.id)
        assert active_run is not None
        assert queued_run is not None
        assert active_run.status == "running"
        assert queued_run.status == "queued"
    finally:
        release.set()
        manager.shutdown()
