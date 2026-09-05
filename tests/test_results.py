from pathlib import Path

from pytest import raises

from app.services.results import ResultParseError, parse_result_directory, parse_result_file


HEADER = (
    "model,ttft,tpot,request_latency,tokens/s,tokens/s/gpu,"
    "num_total_gpus,concurrency,backend,system,parallel\n"
)
DISAGG_HEADER = (
    "model,ttft,tpot,request_latency,tokens/s,tokens/s/gpu,"
    "num_total_gpus,concurrency,(p)backend,(p)system,(d)backend,(d)system,parallel\n"
)


def write_result(path: Path, rows: list[str], *, disagg: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = DISAGG_HEADER if disagg else HEADER
    path.write_text(header + "".join(rows), encoding="utf-8")


def test_parse_file_normalizes_metrics_and_preserves_raw_fields(tmp_path: Path) -> None:
    path = tmp_path / "agg" / "best_config_topn.csv"
    write_result(
        path,
        ["Qwen/Qwen3-32B-FP8,1114.2,29.66,30744,1577.03,1577.03,1,48,trtllm,h200_sxm,tp1\n"],
    )

    results = parse_result_file(
        path,
        "agg",
        ttft_target_ms=2000,
        tpot_target_ms=30,
    )

    assert results[0].rank == 1
    assert results[0].meets_sla is True
    assert results[0].predicted_tokens_per_second == 1577.03
    assert results[0].raw["parallel"] == "tp1"
    assert results[0].source == "best_config_topn.csv"


def test_directory_ranking_prioritizes_sla_then_throughput(tmp_path: Path) -> None:
    write_result(
        tmp_path / "agg" / "best_config_topn.csv",
        [
            "model-a,1000,29,4000,100,50,1,1,trtllm,h200_sxm,tp1\n",
            "model-a,2100,20,3000,999,99,2,2,trtllm,h200_sxm,tp2\n",
        ],
    )
    write_result(
        tmp_path / "disagg" / "best_config_topn.csv",
        ["model-a,900,28,5000,200,40,4,4,trtllm,h200_sxm,trtllm,h200_sxm,tp4\n"],
        disagg=True,
    )

    results = parse_result_directory(
        tmp_path,
        ttft_target_ms=2000,
        tpot_target_ms=30,
    )

    assert [candidate.rank for candidate in results.candidates] == [1, 2, 3]
    assert [
        candidate.predicted_tokens_per_second for candidate in results.candidates
    ] == [200, 100, 999]
    assert [candidate.meets_sla for candidate in results.candidates] == [True, True, False]
    assert results.candidates[0].source == "disagg/best_config_topn.csv"


def test_directory_ranking_is_deterministic_for_ties(tmp_path: Path) -> None:
    write_result(
        tmp_path / "agg" / "best_config_topn.csv",
        ["model-a,1000,29,4000,100,50,2,1,trtllm,h200_sxm,tp1\n"],
    )
    write_result(
        tmp_path / "disagg" / "best_config_topn.csv",
        ["model-a,1000,29,4000,100,50,2,1,trtllm,h200_sxm,trtllm,h200_sxm,tp2\n"],
        disagg=True,
    )

    results = parse_result_directory(tmp_path, ttft_target_ms=2000, tpot_target_ms=30)

    assert [candidate.source for candidate in results.candidates] == [
        "agg/best_config_topn.csv",
        "disagg/best_config_topn.csv",
    ]


def test_parser_rejects_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("model,ttft\nmodel-a,10\n", encoding="utf-8")

    with raises(ResultParseError, match="missing columns"):
        parse_result_file(path, "agg", ttft_target_ms=2000, tpot_target_ms=30)


def test_parser_rejects_non_numeric_metrics(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    write_result(
        path,
        ["model-a,not-a-number,29,4000,100,50,1,1,trtllm,h200_sxm,tp1\n"],
    )

    with raises(ResultParseError, match="Invalid ttft"):
        parse_result_file(path, "agg", ttft_target_ms=2000, tpot_target_ms=30)


def test_directory_requires_at_least_one_supported_result_file(tmp_path: Path) -> None:
    with raises(ResultParseError, match="No supported result files"):
        parse_result_directory(tmp_path, ttft_target_ms=2000, tpot_target_ms=30)
