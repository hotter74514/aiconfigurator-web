from threading import Lock
from uuid import UUID

from app.domain.runs import RunRequest, StoredRun, new_stored_run


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

    def count(self) -> int:
        with self._lock:
            return len(self._runs)
