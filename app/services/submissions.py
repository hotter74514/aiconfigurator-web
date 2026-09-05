from collections.abc import Callable
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread
from uuid import UUID

from app.domain.runs import RunRequest, RunStatus, StoredRun, new_stored_run
from app.services.executor import ExecutionResult, run_aiconfigurator


class RunNotFoundError(LookupError):
    """Raised when a requested run ID is not in the local store."""


class RunTransitionError(ValueError):
    """Raised when a run status transition is not allowed."""


class QueueCapacityError(RuntimeError):
    """Raised when the bounded pending queue has no remaining capacity."""


Runner = Callable[[RunRequest], ExecutionResult]


class RunManager:
    """Store runs and execute them through a bounded local worker pool."""

    def __init__(
        self,
        *,
        runner: Runner = run_aiconfigurator,
        worker_count: int = 1,
        queue_size: int = 10,
        start_workers: bool = True,
    ) -> None:
        if worker_count not in (1, 2):
            raise ValueError("worker_count must be 1 or 2")
        if queue_size < 1:
            raise ValueError("queue_size must be positive")

        self._lock = Lock()
        self._runs: dict[UUID, StoredRun] = {}
        self._queue: Queue[UUID] = Queue(maxsize=queue_size)
        self._runner = runner
        self._stop = Event()
        self._workers: list[Thread] = []

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
            try:
                self._queue.put_nowait(run.id)
            except Full as exc:
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
    ) -> StoredRun:
        with self._lock:
            current = self._runs.get(run_id)
            if current is None:
                raise RunNotFoundError(str(run_id))

            allowed = {
                "queued": {"running"},
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
    ) -> StoredRun:
        return self.transition(run_id, "completed", execution=execution)

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
        for worker in self._workers:
            worker.join(timeout=1)

    def _worker_loop(self) -> None:
        while not self._stop.is_set():
            try:
                run_id = self._queue.get(timeout=0.1)
            except Empty:
                continue

            try:
                run = self.get(run_id)
                if run is None:
                    continue
                self.mark_running(run_id)
                execution = self._runner(run.request)
                if execution.exit_code == 0:
                    self.mark_completed(run_id, execution=execution)
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
                self.mark_failed(run_id, f"Worker execution failed: {exc}")
            finally:
                self._queue.task_done()
