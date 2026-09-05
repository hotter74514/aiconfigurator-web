from dataclasses import dataclass
import math
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from threading import Event

from opentelemetry.trace import Status, StatusCode, set_span_in_context

from app.domain.runs import RunRequest
from app.services.telemetry import get_telemetry, inject_trace_context


@dataclass(frozen=True)
class ExecutionResult:
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False
    cancelled: bool = False


DEFAULT_TIMEOUT_SECONDS = 900.0
TERMINATION_GRACE_SECONDS = 5.0
# Importing the OpenTelemetry SDK in the portal-owned wrapper is part of the
# subprocess boundary, not AIConfigurator execution. Keep short test/runtime
# budgets from expiring while that wrapper starts.
BOOTSTRAP_STARTUP_GRACE_SECONDS = 0.5


def build_aiconfigurator_command(
    request: RunRequest, save_dir: Path | None = None
) -> list[str]:
    """Build the external command without invoking it."""

    command = [
        "aiconfigurator",
        "cli",
        "default",
        "--model",
        request.model,
        "--total-gpus",
        str(request.total_gpus),
        "--system",
        request.system,
        "--ttft",
        str(request.ttft),
        "--tpot",
        str(request.tpot),
    ]
    if save_dir is not None:
        command.extend(("--save-dir", str(save_dir)))
    return command


def build_bootstrap_command(command: list[str]) -> list[str]:
    """Run an unmodified CLI command through the portal trace bootstrap."""

    return [sys.executable, "-m", "app.services.subprocess_bootstrap", *command]


def run_aiconfigurator(
    request: RunRequest,
    save_dir: Path | None = None,
    cancel_event: Event | None = None,
    *,
    timeout_seconds: float | None = None,
    termination_grace_seconds: float = TERMINATION_GRACE_SECONDS,
) -> ExecutionResult:
    """Execute AIConfigurator with timeout and process-group cleanup."""

    started_at = time.monotonic()
    timeout = (
        _configured_timeout_seconds()
        if timeout_seconds is None
        else _validate_seconds("timeout_seconds", timeout_seconds)
    )
    grace_period = _validate_seconds(
        "termination_grace_seconds", termination_grace_seconds
    )
    telemetry = get_telemetry()
    command = build_aiconfigurator_command(request, save_dir)
    subprocess_span = telemetry.tracer.start_span(
        "aiconfigurator.subprocess",
        attributes={
            "subprocess.command": " ".join(command),
            "run.artifact_dir": str(save_dir) if save_dir is not None else "",
        },
    )
    from opentelemetry import context as otel_context

    span_context_token = otel_context.attach(
        set_span_in_context(subprocess_span)
    )
    try:
        popen_kwargs: dict[str, object] = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "env": _subprocess_environment(),
        }
        if os.name == "posix":
            popen_kwargs["start_new_session"] = True
        process = subprocess.Popen(
            build_bootstrap_command(command),
            **popen_kwargs,
        )
    except OSError as exc:
        exit_code = None
        stdout = ""
        stderr = str(exc)
        timed_out = False
        cancelled = False
    else:
        timed_out = False
        cancelled = False
        stdout = ""
        stderr = ""
        while True:
            if (
                cancel_event is not None
                and cancel_event.is_set()
                and process.poll() is None
            ):
                stdout, stderr = _stop_process(process, grace_period)
                cancelled = True
                exit_code = process.returncode
                break

            remaining = timeout + BOOTSTRAP_STARTUP_GRACE_SECONDS - (
                time.monotonic() - started_at
            )
            if remaining <= 0:
                if process.poll() is None:
                    stdout, stderr = _stop_process(process, grace_period)
                    timed_out = True
                else:
                    stdout, stderr = process.communicate()
                exit_code = process.returncode
                break

            try:
                stdout, stderr = process.communicate(timeout=min(0.1, remaining))
                exit_code = process.returncode
                break
            except subprocess.TimeoutExpired:
                continue

    duration_ms = int((time.monotonic() - started_at) * 1000)
    result = ExecutionResult(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_ms=duration_ms,
        timed_out=timed_out,
        cancelled=cancelled,
    )
    outcome = _subprocess_outcome(result)
    subprocess_span.set_attribute(
        "subprocess.exit_code", exit_code if exit_code is not None else -1
    )
    subprocess_span.set_attribute("subprocess.outcome", outcome)
    if result.timed_out or result.cancelled or exit_code not in (0, None):
        subprocess_span.set_status(Status(StatusCode.ERROR, outcome))
    else:
        subprocess_span.set_status(Status(StatusCode.OK))
    subprocess_span.add_event(
        "subprocess.completed",
        attributes={
            "subprocess.outcome": outcome,
            "subprocess.exit_code": exit_code if exit_code is not None else -1,
            "subprocess.duration_ms": duration_ms,
        },
    )
    telemetry.record_subprocess_outcome(outcome)
    otel_context.detach(span_context_token)
    subprocess_span.end()
    return result


def _subprocess_environment() -> dict[str, str]:
    environment = os.environ.copy()
    inject_trace_context(environment)
    return environment


def _subprocess_outcome(result: ExecutionResult) -> str:
    if result.cancelled:
        return "cancelled"
    if result.timed_out:
        return "timeout"
    if result.exit_code == 0:
        return "success"
    if result.exit_code is None:
        return "start_error"
    return "error"


def _configured_timeout_seconds() -> float:
    configured = os.getenv("AICONFIGURATOR_TIMEOUT_SECONDS")
    if configured is None:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        return _validate_seconds("AICONFIGURATOR_TIMEOUT_SECONDS", float(configured))
    except ValueError as exc:
        raise ValueError(
            "AICONFIGURATOR_TIMEOUT_SECONDS must be a positive number"
        ) from exc


def _validate_seconds(name: str, value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _stop_process(
    process: subprocess.Popen[str], grace_period: float
) -> tuple[str, str]:
    if process.poll() is None:
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGTERM)
            else:
                process.terminate()
        except ProcessLookupError:
            pass

    try:
        stdout, stderr = process.communicate(timeout=grace_period)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
    return stdout, stderr
