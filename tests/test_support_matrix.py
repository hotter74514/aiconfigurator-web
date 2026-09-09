import csv

from app.services.support_matrix import load_support_matrix


def write_matrix(path, rows):
    path.mkdir()
    with (path / "h200_sxm.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["HuggingFaceID", "System", "Backend", "Status"],
        )
        writer.writeheader()
        writer.writerows(rows)


def test_load_support_matrix_filters_backend_and_unsupported_rows(tmp_path) -> None:
    write_matrix(
        tmp_path / "matrix",
        [
            {
                "HuggingFaceID": "Qwen/A",
                "System": "h200_sxm",
                "Backend": "trtllm",
                "Status": "PASS",
            },
            {
                "HuggingFaceID": "Qwen/A",
                "System": "h200_sxm",
                "Backend": "trtllm",
                "Status": "HYBRID_PASS",
            },
            {
                "HuggingFaceID": "Qwen/A",
                "System": "h100_sxm",
                "Backend": "vllm",
                "Status": "PASS",
            },
            {
                "HuggingFaceID": "Qwen/B",
                "System": "h200_sxm",
                "Backend": "trtllm",
                "Status": "FAIL",
            },
        ],
    )

    matrix = load_support_matrix(tmp_path / "matrix", package_version="0.11.0")

    assert matrix.source == "installed-wheel"
    assert matrix.aiconfigurator_version == "0.11.0"
    assert matrix.models == ("Qwen/A",)
    assert matrix.systems == ("h200_sxm",)
    assert matrix.pairs[0].status == "PASS"


def test_load_support_matrix_uses_safe_default_without_dependency(tmp_path) -> None:
    matrix = load_support_matrix(tmp_path / "missing")

    assert matrix.source == "fallback-default"
    assert matrix.models == ("Qwen/Qwen3-32B-FP8",)
    assert matrix.systems == ("h200_sxm",)
