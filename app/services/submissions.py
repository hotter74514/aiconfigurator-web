from collections import OrderedDict
from collections.abc import Callable
import logging
import os
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread
from uuid import UUID

from opentelemetry import context as otel_context
from opentelemetry.trace import Span, Status, StatusCode, set_span_in_context

from app.domain.results import RankedResults
from app.domain.runs import (
    RunHistoryItem,
    RunRequest,
    RunStatus,
    StoredRun,
    new_stored_run,
)
from app.services.artifacts import ArtifactStore
from app.services.cache import (
    DEFAULT_CACHE_SIZE,
    CacheIdentity,
    ResultCache,
    build_cache_key,
)
from app.services.executor import (
    TERMINATION_GRACE_SECONDS,
    ExecutionResult,
    run_aiconfigurator,
)
from app.services.logging import bind_run_id, configure_logging, log_event
from app.services.results import parse_result_directory
from app.services.telemetry import PortalTelemetry, get_telemetry


class RunNotFoundError(LookupError):
    """Raised when a requested run ID is not in the local store."""


class RunTransitionError(ValueError):
    """Raised when a run status transition is not allowed."""


class QueueCapacityError(RuntimeError):
    """Raised when the bounded pending queue has no remaining capacity."""


class RunManagerUnavailableError(RuntimeError):
    """Raised when submissions arrive after shutdown has started."""


Runner = Callable[[RunRequest, Path, Event], ExecutionResult]
LOGGER = logging.getLogger("aiconfigurator.portal.runs")
DEFAULT_HISTORY_SIZE = 20


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
        cache: ResultCache | None = None,
        cache_identity: CacheIdentity | None = None,
        cache_size: int = DEFAULT_CACHE_SIZE,
        history_size: int = DEFAULT_HISTORY_SIZE,
    ) -> None:
        configure_logging()
        if worker_count not in (1, 2):
            raise ValueError("worker_count must be 1 or 2")
        if queue_size < 1:
            raise ValueError("queue_size must be positive")
        if history_size < 1:
            raise ValueError("history_size must be positive")

        self._lock = Lock()
        self._runs: dict[UUID, StoredRun] = {}
        self._history_ids: OrderedDict[UUID, None] = OrderedDict()
        self._history_size = history_size
        self._queue: Queue[UUID] = Queue(maxsize=queue_size)
        self._runner = runner
        self._telemetry: PortalTelemetry = get_telemetry()
        self._cache = cache or ResultCache(max_entries=cache_size)
        self._cache_identity = cache_identity or CacheIdentity.from_environment()
        configured_root = artifact_root or os.getenv(
            "AICONFIGURATOR_ARTIFACT_ROOT", ".tmp/runs"
        )
        self._artifacts = ArtifactStore(configured_root)
        self._artifacts.cleanup_expired()
        self._stop = Event()
        self._accepting = True
        self._workers: list[Thread] = []
        self._active_cancellations: dict[UUID, Event] = {}
        self._run_spans: dict[UUID, Span] = {}
        self._queue_wait_spans: dict[UUID, Span] = {}
        self._run_contexts: dict[UUID, otel_context.Context] = {}
        self._telemetry_active_runs: set[UUID] = set()

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
        admission_span = self._telemetry.tracer.start_span(
            "run.admission",
            attributes={"run.id": str(run.id)},
        )
        try:
            with self._lock:
                if not self._accepting:
                    self._telemetry.record_queue_state(
                        admission_span,
                        depth=self._queue.qsize(),
                        capacity=self._queue.maxsize,
                        event_name="run.rejected",
                    )
                    raise RunManagerUnavailableError(
                        "Run manager is shutting down"
                    )
                self._artifacts.prepare_run(run.id)
                try:
                    self._queue.put_nowait(run.id)
                except Full as exc:
                    self._artifacts.remove_run(run.id)
                    self._telemetry.record_queue_state(
                        admission_span,
                        depth=self._queue.maxsize,
                        capacity=self._queue.maxsize,
                        event_name="queue.saturated",
                    )
                    raise QueueCapacityError("Run queue is full") from exc

                run_span = self._telemetry.tracer.start_span(
                    "run",
                    context=set_span_in_context(admission_span),
                    attributes={
                        "run.id": str(run.id),
                        "run.model": request.model,
                        "run.system": request.system,
                    },
                )
                run_context = set_span_in_context(run_span)
                queue_wait_span = self._telemetry.tracer.start_span(
                    "run.queue_wait",
                    context=run_context,
                    attributes={"run.id": str(run.id)},
                )
                self._runs[run.id] = run
                self._run_spans[run.id] = run_span
                self._queue_wait_spans[run.id] = queue_wait_span
                self._run_contexts[run.id] = run_context
                queue_depth = self._queue.qsize()
                self._telemetry.queued_runs.add(1)
                self._telemetry.record_queue_state(
                    run_span,
                    depth=queue_depth,
                    capacity=self._queue.maxsize,
                    event_name="run.queued",
                )
                log_event(
                    LOGGER,
                    "run_queued",
                    run_id=run.id,
                    queue_depth=queue_depth,
                    queue_capacity=self._queue.maxsize,
                )
            return run
        except Exception as exc:
            log_event(
                LOGGER,
                "run_rejected",
                level=logging.WARNING,
                run_id=run.id,
                reason=type(exc).__name__,
            )
            admission_span.record_exception(exc)
            admission_span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
        finally:
            admission_span.end()

    def get(self, run_id: UUID) -> StoredRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def count(self) -> int:
        with self._lock:
            return len(self._runs)

    def history(self) -> list[RunHistoryItem]:
        """Return recent terminal runs, newest first, with live artifact links."""

        with self._lock:
            runs = [
                self._runs[run_id].model_copy(deep=True)
                for run_id in reversed(self._history_ids)
                if run_id in self._runs
            ]

        history: list[RunHistoryItem] = []
        for run in runs:
            available_artifacts: list[str] = []
            artifacts_unavailable = False
            if run.status == "completed" and run.artifacts:
                live_artifacts = set(self._artifacts.list_allowed(run.id))
                available_artifacts = [
                    name for name in run.artifacts if name in live_artifacts
                ]
                artifacts_unavailable = len(available_artifacts) != len(
                    run.artifacts
                )
            history.append(
                RunHistoryItem(
                    id=run.id,
                    status=run.status,
                    request=run.request,
                    created_at=run.created_at,
                    error=run.error,
                    results=run.results,
                    artifacts=available_artifacts,
                    artifacts_unavailable=artifacts_unavailable,
                )
            )
        return history

    def readiness_error(self) -> str | None:
        with self._lock:
            if not self._accepting:
                return "Run manager is shutting down"
            workers = tuple(self._workers)
        if not workers or not all(worker.is_alive() for worker in workers):
            return "Worker initialization is incomplete"
        if not self._artifacts.is_writable():
            return "Artifact storage is not writable"
        return None

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
            self._record_history_locked(updated)
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
        queued_telemetry: list[UUID] = []
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
                    self._record_history_locked(self._runs[run_id])
                    cleanup_ids.append(run_id)
                    queued_telemetry.append(run_id)
            active_cancellations = list(self._active_cancellations.values())
        for _ in queued_telemetry:
            self._telemetry.queued_runs.add(-1)
        for run_id in queued_telemetry:
            self._finish_run_telemetry(run_id, status="failed")
        for cancellation in active_cancellations:
            cancellation.set()

        for worker in self._workers:
            worker.join(timeout=TERMINATION_GRACE_SECONDS + 1)

        running_telemetry: list[UUID] = []
        with self._lock:
            for run_id, run in self._runs.items():
                if run.status == "running":
                    self._runs[run_id] = run.model_copy(
                        update={
                            "status": "failed",
                            "error": "Run cancelled during service shutdown",
                        }
                    )
                    self._record_history_locked(self._runs[run_id])
                    cleanup_ids.append(run_id)
                    running_telemetry.append(run_id)
        for run_id in running_telemetry:
            self._finish_run_telemetry(run_id, status="failed")
        for run_id in cleanup_ids:
            self._artifacts.remove_run(run_id)

    def artifact_dir(self, run_id: UUID) -> Path:
        return self._artifacts.run_dir(run_id)

    def artifact_path(self, run_id: UUID, name: str) -> Path:
        run = self.get(run_id)
        if run is None or run.status != "completed" or name not in run.artifacts:
            raise RunNotFoundError(str(run_id))
        return self._artifacts.resolve_allowed(run_id, name)

    def artifact_bundle_path(self, run_id: UUID) -> Path:
        run = self.get(run_id)
        if run is None or run.status != "completed" or not run.artifacts:
            raise RunNotFoundError(str(run_id))
        return self._artifacts.create_bundle(run_id, run.artifacts)

    def _record_history_locked(self, run: StoredRun) -> None:
        if run.status not in {"completed", "failed"}:
            return
        self._history_ids[run.id] = None
        self._history_ids.move_to_end(run.id)
        while len(self._history_ids) > self._history_size:
            evicted_id, _ = self._history_ids.popitem(last=False)
            evicted = self._runs.get(evicted_id)
            if evicted is not None and evicted.status in {"completed", "failed"}:
                del self._runs[evicted_id]

    def _worker_loop(self) -> None:
        while not self._stop.is_set():
            try:
                run_id = self._queue.get(timeout=0.1)
            except Empty:
                continue

            execution: ExecutionResult | None = None
            try:
                run = self.get(run_id)
                if run is None or run.status != "queued":
                    continue
                run, cancel_event, run_context = self._begin_run(run_id)
                artifact_dir = self._artifacts.run_dir(run_id)
                with bind_run_id(run.id):
                    context_token = otel_context.attach(run_context)
                    try:
                        log_event(LOGGER, "run_started", run_id=run.id)
                        cache_key = build_cache_key(run.request, self._cache_identity)
                        cached = self._cache.get(cache_key)
                        if cached is not None:
                            self._telemetry.record_cache_outcome("hit")
                            log_event(LOGGER, "run_cache_hit", run_id=run.id)
                            restored_artifacts = self._artifacts.restore_allowed(
                                run_id, cached.artifacts
                            )
                            execution = ExecutionResult(
                                exit_code=0,
                                stdout="Result served from deterministic cache",
                                stderr="",
                                duration_ms=0,
                            )
                            updated = self.mark_completed(
                                run_id,
                                execution=execution,
                                results=cached.results,
                                artifacts=restored_artifacts,
                            )
                            self._finish_run_telemetry(
                                run_id,
                                status=updated.status,
                                execution=execution,
                            )
                            continue
                        self._telemetry.record_cache_outcome("miss")
                        execution = self._runner(
                            run.request, artifact_dir, cancel_event
                        )
                    finally:
                        otel_context.detach(context_token)
                current = self.get(run_id)
                if current is None or current.status != "running":
                    continue
                if execution.cancelled:
                    updated = self.mark_failed(
                        run_id,
                        "Run cancelled during service shutdown",
                        execution=execution,
                    )
                    self._finish_run_telemetry(
                        run_id, status=updated.status, execution=execution
                    )
                    self._artifacts.remove_run(run_id)
                elif execution.timed_out:
                    updated = self.mark_failed(
                        run_id,
                        "AIConfigurator timed out",
                        execution=execution,
                    )
                    self._finish_run_telemetry(
                        run_id, status=updated.status, execution=execution
                    )
                    self._artifacts.remove_run(run_id)
                elif execution.exit_code == 0:
                    result_root = self._artifacts.find_result_root(run_id)
                    results = parse_result_directory(
                        result_root,
                        ttft_target_ms=run.request.ttft,
                        tpot_target_ms=run.request.tpot,
                    )
                    artifacts = self._artifacts.list_allowed(run_id)
                    self._cache.put(
                        cache_key,
                        results,
                        self._artifacts.snapshot_allowed(run_id),
                    )
                    updated = self.mark_completed(
                        run_id,
                        execution=execution,
                        results=results,
                        artifacts=artifacts,
                    )
                    self._finish_run_telemetry(
                        run_id, status=updated.status, execution=execution
                    )
                elif execution.exit_code is None:
                    updated = self.mark_failed(
                        run_id,
                        "AIConfigurator process could not start",
                        execution=execution,
                    )
                    self._finish_run_telemetry(
                        run_id, status=updated.status, execution=execution
                    )
                else:
                    updated = self.mark_failed(
                        run_id,
                        f"AIConfigurator exited with status {execution.exit_code}",
                        execution=execution,
                    )
                    self._finish_run_telemetry(
                        run_id, status=updated.status, execution=execution
                    )
            except Exception as exc:  # pragma: no cover - defensive worker boundary
                current = self.get(run_id)
                if current is not None and current.status == "running":
                    updated = self.mark_failed(
                        run_id,
                        f"Worker execution failed: {exc}",
                        execution=execution,
                    )
                    self._finish_run_telemetry(
                        run_id, status=updated.status, execution=execution
                    )
            finally:
                with self._lock:
                    self._active_cancellations.pop(run_id, None)
                self._queue.task_done()

    def _begin_run(
        self, run_id: UUID
    ) -> tuple[StoredRun, Event, otel_context.Context]:
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
            run_context = self._run_contexts[run_id]
            queue_wait_span = self._queue_wait_spans.pop(run_id, None)
            run_span = self._run_spans.get(run_id)
            queue_depth = self._queue.qsize()

        if queue_wait_span is not None:
            queue_wait_span.add_event(
                "run.dequeued",
                attributes={
                    "queue.depth": queue_depth,
                    "queue.capacity": self._queue.maxsize,
                },
            )
            queue_wait_span.end()
        self._telemetry.queued_runs.add(-1)
        self._telemetry.active_runs.add(1)
        self._telemetry_active_runs.add(run_id)
        self._telemetry.record_queue_state(
            run_span,
            depth=queue_depth,
            capacity=self._queue.maxsize,
            event_name="run.dequeued",
        )
        return updated, cancellation, run_context

    def _finish_run_telemetry(
        self,
        run_id: UUID,
        *,
        status: str,
        execution: ExecutionResult | None = None,
    ) -> None:
        with self._lock:
            run_span = self._run_spans.pop(run_id, None)
            queue_wait_span = self._queue_wait_spans.pop(run_id, None)
            run_context = self._run_contexts.pop(run_id, None)
            active = run_id in self._telemetry_active_runs
            self._telemetry_active_runs.discard(run_id)
            run = self._runs.get(run_id)

        if queue_wait_span is not None:
            queue_wait_span.end()
        context_token = (
            otel_context.attach(run_context) if run_context is not None else None
        )
        try:
            if run_span is not None:
                attributes: dict[str, str | int] = {"run.status": status}
                if execution is not None:
                    attributes["run.duration_ms"] = execution.duration_ms
                run_span.add_event("run.terminal", attributes=attributes)
                run_span.set_attribute("run.status", status)
                if status == "failed":
                    run_span.set_status(
                        Status(StatusCode.ERROR, run.error if run else None)
                    )
                else:
                    run_span.set_status(Status(StatusCode.OK))
                log_event(
                    LOGGER,
                    "run_terminal",
                    level=logging.INFO if status == "completed" else logging.WARNING,
                    run_id=run_id,
                    status=status,
                    duration_ms=execution.duration_ms if execution else None,
                    error=run.error if run and status == "failed" else None,
                )
                run_span.end()
            else:
                log_event(
                    LOGGER,
                    "run_terminal",
                    level=logging.INFO if status == "completed" else logging.WARNING,
                    run_id=run_id,
                    status=status,
                    duration_ms=execution.duration_ms if execution else None,
                    error=run.error if run and status == "failed" else None,
                )
        finally:
            if context_token is not None:
                otel_context.detach(context_token)

        duration_ms = execution.duration_ms if execution is not None else None
        self._telemetry.record_terminal_run(
            status,
            duration_ms=duration_ms,
            active=active,
            context=run_context,
        )
        if status == "completed" and run is not None:
            self._telemetry.record_artifact_bytes(
                self._artifacts.total_allowed_bytes(run_id)
            )
