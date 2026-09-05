import json
import logging

from app.services.logging import JsonLogFormatter, bind_run_id
from app.services.telemetry import get_telemetry


def test_json_logs_include_trace_span_and_run_correlation() -> None:
    logger = logging.getLogger("aiconfigurator.portal.test")
    formatter = JsonLogFormatter()
    telemetry = get_telemetry()

    with telemetry.tracer.start_as_current_span("test-log"):
        with bind_run_id("run-123"):
            record = logger.makeRecord(
                logger.name,
                logging.INFO,
                __file__,
                1,
                "run_started",
                (),
                None,
                extra={
                    "structured": {
                        "event": "run_started",
                        "queue_depth": 2,
                    }
                },
            )
            payload = json.loads(formatter.format(record))

    assert payload["event"] == "run_started"
    assert payload["run_id"] == "run-123"
    assert len(payload["trace_id"]) == 32
    assert len(payload["span_id"]) == 16
    assert payload["queue_depth"] == 2
