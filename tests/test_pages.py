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


def test_index_keeps_polling_and_result_rendering_out_of_scope() -> None:
    client = TestClient(create_app(RunManager(start_workers=False)))

    response = client.get("/")

    assert "setInterval" not in response.text
    assert "ranked-results" not in response.text
