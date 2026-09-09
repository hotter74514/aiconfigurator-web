from fastapi.testclient import TestClient

from app.main import create_app
from app.services.submissions import RunManager


def test_support_endpoint_exposes_selectable_matrix() -> None:
    client = TestClient(create_app(RunManager(start_workers=False)))

    response = client.get("/api/support")

    assert response.status_code == 200
    body = response.json()
    assert body["backend"] == "trtllm"
    assert body["source"] == "fallback-default"
    assert body["models"] == ["Qwen/Qwen3-32B-FP8"]
    assert body["systems"] == ["h200_sxm"]
    assert body["pairs"] == [
        {
            "model": "Qwen/Qwen3-32B-FP8",
            "system": "h200_sxm",
            "status": "PASS",
        }
    ]
