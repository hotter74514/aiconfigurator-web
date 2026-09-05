import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.domain.results import RankedResult, RankedResults, ResultMode


COMMON_COLUMNS = frozenset(
    {
        "model",
        "ttft",
        "tpot",
        "request_latency",
        "tokens/s",
        "tokens/s/gpu",
        "num_total_gpus",
        "concurrency",
    }
)


class ResultParseError(ValueError):
    """Raised when AIConfigurator structured output is not parseable."""


@dataclass(frozen=True)
class _ParsedCandidate:
    mode: ResultMode
    source: str
    model: str
    meets_sla: bool
    tokens_per_second: float
    tokens_per_second_per_gpu: float
    ttft_ms: float
    tpot_ms: float
    request_latency_ms: float
    total_gpus: int
    concurrency: float
    backend: str
    system: str
    raw: dict[str, str]
    source_order: int


def parse_result_file(
    path: Path,
    mode: ResultMode,
    *,
    ttft_target_ms: float,
    tpot_target_ms: float,
    source: str | None = None,
) -> list[RankedResult]:
    """Parse one `best_config_topn.csv` file without scraping CLI stdout.

    The returned ranks are local to this file. Use `parse_result_directory`
    when aggregate and disaggregate candidates need one combined ranking.
    """

    _validate_mode(mode)
    _validate_targets(ttft_target_ms, tpot_target_ms)
    parsed = _read_candidates(
        path,
        mode,
        ttft_target_ms=ttft_target_ms,
        tpot_target_ms=tpot_target_ms,
        source=source or path.name,
    )
    return _rank_candidates(parsed)


def parse_result_directory(
    root: Path,
    *,
    ttft_target_ms: float,
    tpot_target_ms: float,
) -> RankedResults:
    """Parse and rank the structured results for one AIConfigurator run.

    Only the stable `best_config_topn.csv` files are consumed. Other files
    remain raw artifacts for TASK-017 and are deliberately not parsed here.
    """

    _validate_targets(ttft_target_ms, tpot_target_ms)
    root = Path(root)
    candidates: list[_ParsedCandidate] = []
    source_order = 0

    for mode in ("agg", "disagg"):
        result_path = root / mode / "best_config_topn.csv"
        if not result_path.is_file():
            continue
        candidates.extend(
            _read_candidates(
                result_path,
                mode,
                ttft_target_ms=ttft_target_ms,
                tpot_target_ms=tpot_target_ms,
                source=result_path.relative_to(root).as_posix(),
                source_order_start=source_order,
            )
        )
        source_order = len(candidates)

    if not candidates:
        raise ResultParseError(
            f"No supported result files found below {root}: "
            "expected agg/best_config_topn.csv or "
            "disagg/best_config_topn.csv"
        )

    models = {candidate.model for candidate in candidates}
    if len(models) != 1:
        raise ResultParseError(
            "Result files contain multiple model values: "
            + ", ".join(sorted(models))
        )

    ranked = _rank_candidates(candidates)
    return RankedResults(
        model=candidates[0].model,
        ttft_target_ms=ttft_target_ms,
        tpot_target_ms=tpot_target_ms,
        candidates=ranked,
    )


def _read_candidates(
    path: Path,
    mode: ResultMode,
    *,
    ttft_target_ms: float,
    tpot_target_ms: float,
    source: str,
    source_order_start: int = 0,
) -> list[_ParsedCandidate]:
    if not path.is_file():
        raise ResultParseError(f"Result file does not exist: {path}")

    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            fieldnames = reader.fieldnames
            if fieldnames is None:
                raise ResultParseError(f"Result file has no header: {path}")

            normalized_headers = [header.strip() for header in fieldnames]
            duplicates = _duplicates(normalized_headers)
            if duplicates:
                raise ResultParseError(
                    f"Result file has duplicate columns {sorted(duplicates)}: {path}"
                )
            missing = COMMON_COLUMNS - set(normalized_headers)
            if mode == "agg":
                missing |= {
                    name
                    for name in ("backend", "system")
                    if name not in normalized_headers
                }
            else:
                for logical_name, alternatives in (
                    ("backend", ("(p)backend", "(d)backend")),
                    ("system", ("(p)system", "(d)system")),
                ):
                    if not any(name in normalized_headers for name in alternatives):
                        missing.add(logical_name)
            if missing:
                raise ResultParseError(
                    f"Result file is missing columns {sorted(missing)}: {path}"
                )

            candidates: list[_ParsedCandidate] = []
            for line_number, row in enumerate(reader, start=2):
                if row is None or all(not (value or "").strip() for value in row.values()):
                    continue
                if None in row:
                    raise ResultParseError(
                        f"Result file has extra fields on line {line_number}: {path}"
                    )
                normalized = {
                    key.strip(): (value or "").strip()
                    for key, value in row.items()
                    if key is not None
                }
                candidates.append(
                    _parse_candidate(
                        normalized,
                        mode,
                        source=source,
                        line_number=line_number,
                        ttft_target_ms=ttft_target_ms,
                        tpot_target_ms=tpot_target_ms,
                        source_order=source_order_start + len(candidates),
                    )
                )
    except (OSError, csv.Error) as exc:
        raise ResultParseError(f"Could not read result file {path}: {exc}") from exc

    if not candidates:
        raise ResultParseError(f"Result file has no data rows: {path}")
    return candidates


def _parse_candidate(
    row: dict[str, str],
    mode: ResultMode,
    *,
    source: str,
    line_number: int,
    ttft_target_ms: float,
    tpot_target_ms: float,
    source_order: int,
) -> _ParsedCandidate:
    context = f"{source} line {line_number}"
    model = row["model"]
    if not model:
        raise ResultParseError(f"Missing model in {context}")

    ttft_ms = _parse_non_negative_float(row["ttft"], "ttft", context)
    tpot_ms = _parse_non_negative_float(row["tpot"], "tpot", context)
    return _ParsedCandidate(
        mode=mode,
        source=source,
        model=model,
        meets_sla=ttft_ms <= ttft_target_ms and tpot_ms <= tpot_target_ms,
        tokens_per_second=_parse_non_negative_float(row["tokens/s"], "tokens/s", context),
        tokens_per_second_per_gpu=_parse_non_negative_float(
            row["tokens/s/gpu"], "tokens/s/gpu", context
        ),
        ttft_ms=ttft_ms,
        tpot_ms=tpot_ms,
        request_latency_ms=_parse_non_negative_float(
            row["request_latency"], "request_latency", context
        ),
        total_gpus=_parse_positive_int(row["num_total_gpus"], "num_total_gpus", context),
        concurrency=_parse_non_negative_float(row["concurrency"], "concurrency", context),
        backend=_mode_value(row, mode, "backend", context),
        system=_mode_value(row, mode, "system", context),
        raw=row,
        source_order=source_order,
    )


def _rank_candidates(candidates: Iterable[_ParsedCandidate]) -> list[RankedResult]:
    ordered = sorted(
        candidates,
        key=lambda candidate: (
            0 if candidate.meets_sla else 1,
            -candidate.tokens_per_second,
            candidate.request_latency_ms,
            candidate.total_gpus,
            candidate.mode,
            candidate.source,
            candidate.source_order,
        ),
    )
    return [
        RankedResult(
            rank=index,
            mode=candidate.mode,
            source=candidate.source,
            meets_sla=candidate.meets_sla,
            predicted_tokens_per_second=candidate.tokens_per_second,
            predicted_tokens_per_second_per_gpu=candidate.tokens_per_second_per_gpu,
            predicted_ttft_ms=candidate.ttft_ms,
            predicted_tpot_ms=candidate.tpot_ms,
            predicted_request_latency_ms=candidate.request_latency_ms,
            total_gpus=candidate.total_gpus,
            concurrency=candidate.concurrency,
            backend=candidate.backend,
            system=candidate.system,
            raw=candidate.raw,
        )
        for index, candidate in enumerate(ordered, start=1)
    ]


def _parse_float(value: str, field: str, context: str) -> float:
    if not value:
        raise ResultParseError(f"Missing {field} in {context}")
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ResultParseError(
            f"Invalid {field}={value!r} in {context}"
        ) from exc
    if not math.isfinite(parsed):
        raise ResultParseError(f"Non-finite {field}={value!r} in {context}")
    return parsed


def _parse_positive_int(value: str, field: str, context: str) -> int:
    parsed = _parse_float(value, field, context)
    if parsed <= 0 or not parsed.is_integer():
        raise ResultParseError(f"Expected positive integer {field} in {context}")
    return int(parsed)


def _parse_non_negative_float(value: str, field: str, context: str) -> float:
    parsed = _parse_float(value, field, context)
    if parsed < 0:
        raise ResultParseError(f"Expected non-negative {field} in {context}")
    return parsed


def _mode_value(
    row: dict[str, str], mode: ResultMode, field: str, context: str
) -> str:
    names = (field,) if mode == "agg" else (f"(p){field}", f"(d){field}")
    for name in names:
        value = row.get(name, "")
        if value:
            return value
    raise ResultParseError(f"Missing {field} in {context}")


def _validate_targets(ttft_target_ms: float, tpot_target_ms: float) -> None:
    for name, value in (("ttft_target_ms", ttft_target_ms), ("tpot_target_ms", tpot_target_ms)):
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a positive finite number")


def _validate_mode(mode: ResultMode) -> None:
    if mode not in ("agg", "disagg"):
        raise ValueError("mode must be 'agg' or 'disagg'")


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates
