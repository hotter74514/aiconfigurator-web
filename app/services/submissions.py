from collections.abc import Callable
import os
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread
from uuid import UUID

from app.domain.results import RankedResults
from app.domain.runs import RunRequest, RunStatus, StoredRun, new_stored_run
from app.services.artifacts import ArtifactStore
from app.services.executor import (
    TERMINATION_GRACE_SECONDS,
    ExecutionResult,
    run_aiconfigurator,
)
from app.services.results import parse_result_directory


class RunNotFoundError(LookupError):
    """Raised when a requested run ID is not in the local store."""


class RunTransitionError(ValueError):
    """Raised when a run status transition is not allowed."""


class QueueCapacityError(RuntimeError):
    """Raised when the bounded pending queue has no remaining capacity."""


class RunManagerUnavailableError(RuntimeError):
    """Raised when submissions arrive after shutdown has started."""


Runner = Callable[[RunRequest, Path, Event], ExecutionResult]


class RunManager:
    """Store runs and execute them through a bounded local worker pool."""

    def __init__(
        self,
        *,
        runner: Runner = run_aiconfigurator,
        worker_count: int = 1,
        queue_size: int = 10,
        start_workers: bool = True,
        artifact_root: Path | str | None = None,
    ) -> None:
        if worker_count not in (1, 2):
            raise ValueError("worker_count must be 1 or 2")
        if queue_size < 1:
            raise ValueError("queue_size must be positive")

        self._lock = Lock()
        self._runs: dict[UUID, StoredRun] = {}
        self._queue: Queue[UUID] = Queue(maxsize=queue_size)
        self._runner = runner
        configured_root = artifact_root or os.getenv(
            "AICONFIGURATOR_ARTIFACT_ROOT", ".tmp/runs"
        )
        self._artifacts = ArtifactStore(configured_root)
        self._artifacts.cleanup_expired()
        self._stop = Event()
        self._accepting = True
        self._workers: list[Thread] = []
        self._active_cancellations: dict[UUID, Event] = {}

        if start_workers:
            for index in range(worker_count):
                worker = Thread(
                    target=self._worker_loop,
                    name=f"aiconfigurator-worker-{index + 1}",
                    daemon=True,
                )
                worker.start()
                self._workers.append(worker)

    def submit(self, request: RunRequest) -> StoredRun:
        run = new_stored_run(request)
        with self._lock:
            if not self._accepting:
                raise RunManagerUnavailableError("Run manager is shutting down")
            self._artifacts.prepare_run(run.id)
            try:
                self._queue.put_nowait(run.id)
            except Full as exc:
                self._artifacts.remove_run(run.id)
                raise QueueCapacityError("Run queue is full") from exc
            self._runs[run.id] = run
        return run

    def get(self, run_id: UUID) -> StoredRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def count(self) -> int:
        with self._lock:
            return len(self._runs)

    def transition(
        self,
        run_id: UUID,
        status: RunStatus,
        *,
        error: str | None = None,
        execution: ExecutionResult | None = None,
        results: RankedResults | None = None,
        artifacts: list[str] | None = None,
    ) -> StoredRun:
        with self._lock:
            current = self._runs.get(run_id)
            if current is None:
                raise RunNotFoundError(str(run_id))

            allowed = {
                "queued": {"running", "failed"},
                "running": {"completed", "failed"},
                "completed": set(),
                "failed": set(),
            }
            if status not in allowed[current.status]:
                raise RunTransitionError(
                    f"Cannot transition run {run_id} from "
                    f"{current.status} to {status}"
                )

            updates: dict[str, object] = {"status": status, "error": error}
            if execution is not None:
                updates.update(
                    {
                        "stdout": execution.stdout,
                        "stderr": execution.stderr,
                        "exit_code": execution.exit_code,
                        "duration_ms": execution.duration_ms,
                    }
                )
            if results is not None:
                updates["results"] = results
            if artifacts is not None:
                updates["artifacts"] = artifacts
            updated = current.model_copy(update=updates)
            self._runs[run_id] = updated
            return updated

    def mark_running(self, run_id: UUID) -> StoredRun:
        return self.transition(run_id, "running")

    def mark_completed(
        self,
        run_id: UUID,
        *,
        execution: ExecutionResult | None = None,
        results: RankedResults | None = None,
        artifacts: list[str] | None = None,
    ) -> StoredRun:
        return self.transition(
            run_id,
            "completed",
            execution=execution,
            results=results,
            artifacts=artifacts,
        )

    def mark_failed(
        self,
        run_id: UUID,
        error: str,
        *,
        execution: ExecutionResult | None = None,
    ) -> StoredRun:
        return self.transition(run_id, "failed", error=error, execution=execution)

    def shutdown(self) -> None:
        self._stop.set()

        cleanup_ids: list[UUID] = []
        with self._lock:
            self._accepting = False
            for run_id, run in self._runs.items():
                if run.status == "queued":
                    self._runs[run_id] = run.model_copy(
                        update={
                            "status": "failed",
                            "error": "Run cancelled during service shutdown",
                        }
                    )
                    cleanup_ids.append(run_id)
            active_cancellations = list(self._active_cancellations.values())
        for cancellation in active_cancellations:
            cancellation.set()

        for worker in self._workers:
            worker.join(timeout=TERMINATION_GRACE_SECONDS + 1)

        with self._lock:
            for run_id, run in self._runs.items():
                if run.status == "running":
                    self._runs[run_id] = run.model_copy(
                        update={
                            "status": "failed",
                            "error": "Run cancelled during service shutdown",
                        }
                    )
                    cleanup_ids.append(run_id)
        for run_id in cleanup_ids:
            self._artifacts.remove_run(run_id)

    def artifact_dir(self, run_id: UUID) -> Path:
        return self._artifacts.run_dir(run_id)

    def artifact_path(self, run_id: UUID, name: str) -> Path:
        run = self.get(run_id)
        if run is None or run.status != "completed" or name not in run.artifacts:
            raise RunNotFoundError(str(run_id))
        return self._artifacts.resolve_allowed(run_id, name)

    def _worker_loop(self) -> None:
        while not self._stop.is_set():
            try:
                run_id = self._queue.get(timeout=0.1)
            except Empty:
                continue

            try:
                run = self.get(run_id)
                if run is None or run.status != "queued":
                    continue
                run, cancel_event = self._begin_run(run_id)
                artifact_dir = self._artifacts.run_dir(run_id)
                execution = self._runner(run.request, artifact_dir, cancel_event)
                current = self.get(run_id)
                if current is None or current.status != "running":
                    continue
                if execution.cancelled:
                    self.mark_failed(
                        run_id,
                        "Run cancelled during service shutdown",
                        execution=execution,
                    )
                    self._artifacts.remove_run(run_id)
                elif execution.timed_out:
                    self.mark_failed(
                        run_id,
                        "AIConfigurator timed out",
                        execution=execution,
                    )
                    self._artifacts.remove_run(run_id)
                elif execution.exit_code == 0:
                    result_root = self._artifacts.find_result_root(run_id)
                    results = parse_result_directory(
                        result_root,
                        ttft_target_ms=run.request.ttft,
                        tpot_target_ms=run.request.tpot,
                    )
                    self.mark_completed(
                        run_id,
                        execution=execution,
                        results=results,
                        artifacts=self._artifacts.list_allowed(run_id),
                    )
                elif execution.exit_code is None:
                    self.mark_failed(
                        run_id,
                        "AIConfigurator process could not start",
                        execution=execution,
                    )
                else:
                    self.mark_failed(
                        run_id,
                        f"AIConfigurator exited with status {execution.exit_code}",
                        execution=execution,
                    )
            except Exception as exc:  # pragma: no cover - defensive worker boundary
                current = self.get(run_id)
                if current is not None and current.status == "running":
                    self.mark_failed(run_id, f"Worker execution failed: {exc}")
            finally:
                with self._lock:
                    self._active_cancellations.pop(run_id, None)
                self._queue.task_done()

    def _begin_run(self, run_id: UUID) -> tuple[StoredRun, Event]:
        with self._lock:
            current = self._runs.get(run_id)
            if current is None:
                raise RunNotFoundError(str(run_id))
            if current.status != "queued":
                raise RunTransitionError(
                    f"Cannot start run {run_id} from {current.status}"
                )
            updated = current.model_copy(update={"status": "running", "error": None})
            cancellation = Event()
            self._runs[run_id] = updated
            self._active_cancellations[run_id] = cancellation
            return updated, cancellation
