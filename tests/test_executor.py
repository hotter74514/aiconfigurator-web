import sys
import time
from pathlib import Path
from threading import Event, Thread

import app.services.executor as executor
from app.domain.runs import RunRequest


def make_request() -> RunRequest:
    return RunRequest(
        model="Qwen/Qwen3-32B-FP8",
        system="h200_sxm",
        total_gpus=32,
        ttft=2000,
        tpot=30,
    )


def sleep_command(_: RunRequest, __: Path | None = None) -> list[str]:
    return [
        sys.executable,
        "-c",
        "import time; print('child-started', flush=True); time.sleep(10)",
    ]


def test_executor_times_out_and_terminates_process_group(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(executor, "build_aiconfigurator_command", sleep_command)

    result = executor.run_aiconfigurator(
        make_request(),
        tmp_path,
        timeout_seconds=0.1,
        termination_grace_seconds=0.1,
    )

    assert result.timed_out is True
    assert result.cancelled is False
    assert result.stdout.strip() == "child-started"
    assert result.duration_ms < 2000


def test_executor_cancellation_terminates_process_group(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(executor, "build_aiconfigurator_command", sleep_command)
    cancel_event = Event()
    results = []

    def run() -> None:
        results.append(
            executor.run_aiconfigurator(
                make_request(),
                tmp_path,
                cancel_event,
                timeout_seconds=10,
                termination_grace_seconds=0.1,
            )
        )

    thread = Thread(target=run)
    thread.start()
    time.sleep(0.1)
    cancel_event.set()
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert len(results) == 1
    assert results[0].cancelled is True
    assert results[0].timed_out is False
