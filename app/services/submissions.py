from threading import Lock
from uuid import UUID

from app.domain.runs import RunRequest, RunStatus, StoredRun, new_stored_run


class RunNotFoundError(LookupError):
    """Raised when a requested run ID is not in the local store."""


class RunTransitionError(ValueError):
    """Raised when a run status transition is not allowed."""


class InMemoryRunSubmissionService:
    """Create queued run records until the worker task is implemented."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._runs: dict[UUID, StoredRun] = {}

    def submit(self, request: RunRequest) -> StoredRun:
        run = new_stored_run(request)
        with self._lock:
            self._runs[run.id] = run
        return run

    def get(self, run_id: UUID) -> StoredRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def transition(
        self,
        run_id: UUID,
        status: RunStatus,
        *,
        error: str | None = None,
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

            updated = current.model_copy(update={"status": status, "error": error})
            self._runs[run_id] = updated
            return updated

    def mark_running(self, run_id: UUID) -> StoredRun:
        return self.transition(run_id, "running")

    def mark_completed(self, run_id: UUID) -> StoredRun:
        return self.transition(run_id, "completed")

    def mark_failed(self, run_id: UUID, error: str) -> StoredRun:
        return self.transition(run_id, "failed", error=error)

    def count(self) -> int:
        with self._lock:
            return len(self._runs)
