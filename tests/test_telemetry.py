import re
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

import app.services.executor as executor
from app.domain.runs import RunRequest
from app.main import create_app
from app.services.executor import ExecutionResult, run_aiconfigurator
from app.services.submissions import RunManager
from app.services.telemetry import get_telemetry


def make_request() -> RunRequest:
    return RunRequest(
        model="Qwen/Qwen3-32B-FP8",
        system="h200_sxm",
        total_gpus=32,
        ttft=2000,
        tpot=30,
    )


def test_metrics_endpoint_exposes_http_and_queue_metrics(tmp_path: Path) -> None:
    service = RunManager(start_workers=False, artifact_root=tmp_path / "runs")
    try:
        client = TestClient(create_app(service))
        assert client.get("/live").status_code == 200
        run = service.submit(make_request())

        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith(
            "application/openmetrics-text"
        )
        assert "http_server_duration_milliseconds" in response.text
        assert "portal_queue_depth" in response.text
        queue_lines = [
            line
            for line in response.text.splitlines()
            if line.startswith("portal_queue_depth{")
        ]
        assert len(queue_lines) == 1
        assert float(queue_lines[0].rsplit(" ", 1)[1]) >= 1
        assert str(run.id) not in response.text
    finally:
        service.shutdown()


def test_completed_run_records_artifact_bytes(tmp_path: Path) -> None:
    def successful_runner(
        _: RunRequest, save_dir: Path, __
    ) -> ExecutionResult:
        result_dir = save_dir / "agg"
        result_dir.mkdir(parents=True)
        (result_dir / "best_config_topn.csv").write_text(
            "model,ttft,tpot,request_latency,tokens/s,tokens/s/gpu,"
            "num_total_gpus,concurrency,backend,system\n"
            "m,1,1,1,1,1,1,1,b,s\n",
            encoding="utf-8",
        )
        return ExecutionResult(0, "", "", 1)

    service = RunManager(
        runner=successful_runner,
        artifact_root=tmp_path / "runs",
    )
    try:
        run = service.submit(make_request())
        for _ in range(200):
            current = service.get(run.id)
            if current is not None and current.status == "completed":
                break
            time.sleep(0.01)
        metrics = TestClient(create_app(service)).get("/metrics").text
    finally:
        service.shutdown()

    assert "portal_artifact_bytes_total" in metrics
    artifact_lines = [
        line
        for line in metrics.splitlines()
        if line.startswith("portal_artifact_bytes_total{")
    ]
    assert len(artifact_lines) == 1
    assert float(artifact_lines[0].rsplit(" ", 1)[1]) > 0


def test_completed_run_exposes_trace_id_exemplar(tmp_path: Path) -> None:
    def successful_runner(
        _: RunRequest, save_dir: Path, __
    ) -> ExecutionResult:
        result_dir = save_dir / "agg"
        result_dir.mkdir(parents=True)
        (result_dir / "best_config_topn.csv").write_text(
            "model,ttft,tpot,request_latency,tokens/s,tokens/s/gpu,"
            "num_total_gpus,concurrency,backend,system\n"
            "m,1,1,1,1,1,1,1,b,s\n",
            encoding="utf-8",
        )
        return ExecutionResult(0, "", "", 1)

    service = RunManager(
        runner=successful_runner,
        artifact_root=tmp_path / "runs",
    )
    try:
        run = service.submit(make_request())
        for _ in range(200):
            current = service.get(run.id)
            if current is not None and current.status == "completed":
                break
            time.sleep(0.01)
        metrics = TestClient(create_app(service)).get("/metrics").text
    finally:
        service.shutdown()

    assert re.search(
        r'portal_trace_run_duration_seconds_bucket\{[^}]*\} '
        r'[^#]+# \{trace_id="[0-9a-f]{32}"\}',
        metrics,
    )


def test_subprocess_wrapper_propagates_parent_trace_id(
    monkeypatch, tmp_path: Path
) -> None:
    def trace_id_command(_: RunRequest, __: Path | None = None) -> list[str]:
        return [
            sys.executable,
            "-c",
            "import os; "
            "print(os.environ['TRACEPARENT'].split('-')[1], flush=True)",
        ]

    monkeypatch.setattr(executor, "build_aiconfigurator_command", trace_id_command)
    telemetry = get_telemetry()

    with telemetry.tracer.start_as_current_span("test-parent") as parent:
        expected_trace_id = format(
            parent.get_span_context().trace_id,
            "032x",
        )
        result = run_aiconfigurator(
            make_request(),
            tmp_path,
            timeout_seconds=2,
            termination_grace_seconds=0.1,
        )

    assert result.exit_code == 0
    assert result.stdout.strip() == expected_trace_id
