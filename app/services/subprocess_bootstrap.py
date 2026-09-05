import os
import logging
import subprocess
import sys

from opentelemetry.trace import Status, StatusCode

from app.services.telemetry import (
    extract_trace_context,
    get_telemetry,
    inject_trace_context,
)
from app.services.logging import RUN_ID_ENV, configure_logging, log_event

LOGGER = logging.getLogger("aiconfigurator.portal.subprocess")


def main(argv: list[str] | None = None) -> int:
    command = list(sys.argv[1:] if argv is None else argv)
    if not command:
        print("subprocess bootstrap requires a command", file=sys.stderr)
        return 2

    telemetry = get_telemetry()
    configure_logging()
    parent_context = extract_trace_context(dict(os.environ))
    exit_code = 127
    with telemetry.tracer.start_as_current_span(
        "aiconfigurator.cli",
        context=parent_context,
        attributes={"subprocess.command": " ".join(command)},
    ) as span:
        try:
            child_environment = os.environ.copy()
            inject_trace_context(child_environment)
            log_event(
                LOGGER,
                "subprocess_started",
                run_id=os.environ.get(RUN_ID_ENV),
                command=command[0],
            )
            completed = subprocess.run(
                command,
                check=False,
                env=child_environment,
            )
        except OSError as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
        else:
            exit_code = completed.returncode
            span.set_attribute("subprocess.exit_code", completed.returncode)
            span.set_status(
                Status(
                    StatusCode.OK if completed.returncode == 0 else StatusCode.ERROR,
                    None
                    if completed.returncode == 0
                    else "child command failed",
                )
            )
            span.add_event(
                "aiconfigurator.cli.completed",
                attributes={"subprocess.exit_code": completed.returncode},
            )
            log_event(
                LOGGER,
                "subprocess_child_completed",
                level=logging.INFO
                if completed.returncode == 0
                else logging.WARNING,
                run_id=os.environ.get(RUN_ID_ENV),
                exit_code=completed.returncode,
            )

    telemetry.force_flush()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
