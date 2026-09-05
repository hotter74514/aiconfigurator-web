from dataclasses import dataclass
import subprocess
import time
from pathlib import Path

from app.domain.runs import RunRequest


@dataclass(frozen=True)
class ExecutionResult:
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: int


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


def run_aiconfigurator(
    request: RunRequest, save_dir: Path | None = None
) -> ExecutionResult:
    """Execute AIConfigurator and capture its process result."""

    started_at = time.monotonic()
    try:
        completed = subprocess.run(
            build_aiconfigurator_command(request, save_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except OSError as exc:
        exit_code = None
        stdout = ""
        stderr = str(exc)

    duration_ms = int((time.monotonic() - started_at) * 1000)
    return ExecutionResult(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_ms=duration_ms,
    )
