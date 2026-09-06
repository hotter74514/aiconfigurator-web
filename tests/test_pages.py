from fastapi.testclient import TestClient

from app.main import create_app
from app.services.submissions import RunManager


def test_index_renders_plain_jinja_form() -> None:
    client = TestClient(create_app(RunManager(start_workers=False)))

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'name="model"' in response.text
    assert 'name="system"' in response.text
    assert 'name="total_gpus"' in response.text
    assert 'name="ttft"' in response.text
    assert 'name="tpot"' in response.text
    assert 'value="Qwen/Qwen3-32B-FP8"' in response.text
    assert 'data-endpoint="/api/runs"' in response.text
    assert '<link rel="icon" href="data:,">' in response.text
    assert "predictions must be validated" in response.text


def test_index_contains_status_polling_and_result_rendering() -> None:
    client = TestClient(create_app(RunManager(start_workers=False)))

    response = client.get("/")

    assert "POLL_INTERVAL_MS = 2000" in response.text
    assert "setTimeout" in response.text
    assert "GET /api/runs/" not in response.text
    assert 'id="results-panel"' in response.text
    assert 'id="results-body"' in response.text
    assert 'id="artifact-list"' in response.text
    assert "renderResults" in response.text
    assert "Estimate warning" in response.text


def test_index_contains_pareto_frontier_visualization_contract() -> None:
    client = TestClient(create_app(RunManager(start_workers=False)))

    response = client.get("/")

    assert response.status_code == 200
    assert 'id="pareto-panel"' in response.text
    assert 'id="pareto-chart"' in response.text
    assert 'id="pareto-frontier-list"' in response.text
    assert "Throughput vs. request latency" in response.text
    assert "isParetoDominated" in response.text
    assert "renderParetoChart" in response.text


def test_index_contains_aggregate_disaggregated_comparison_contract() -> None:
    client = TestClient(create_app(RunManager(start_workers=False)))

    response = client.get("/")

    assert response.status_code == 200
    assert 'id="comparison-panel"' in response.text
    assert 'id="agg-comparison-card"' in response.text
    assert 'id="disagg-comparison-card"' in response.text
    assert 'id="agg-comparison-throughput"' in response.text
    assert 'id="disagg-comparison-latency"' in response.text
    assert "renderModeCard" in response.text
    assert "renderModeComparison" in response.text
    assert "Comparison is incomplete" in response.text
