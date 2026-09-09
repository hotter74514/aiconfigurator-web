"""Read the installed AIConfigurator support matrix for portal choices."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import csv
from importlib import metadata
from importlib.util import find_spec
from pathlib import Path


DEFAULT_BACKEND = "trtllm"
SUPPORTED_STATUSES = frozenset({"PASS", "HYBRID_PASS"})
_STATUS_PRIORITY = {"HYBRID_PASS": 1, "PASS": 2}


@dataclass(frozen=True)
class SupportPair:
    model: str
    system: str
    status: str


@dataclass(frozen=True)
class SupportMatrix:
    backend: str
    source: str
    aiconfigurator_version: str | None
    models: tuple[str, ...]
    systems: tuple[str, ...]
    pairs: tuple[SupportPair, ...]


def load_support_matrix(
    matrix_dir: Path | None = None,
    *,
    backend: str = DEFAULT_BACKEND,
    package_version: str | None = None,
) -> SupportMatrix:
    """Load supported model/system pairs from the installed wheel.

    The portal invokes AIConfigurator's default command, whose backend is
    TRT-LLM unless explicitly overridden. Only PASS and HYBRID_PASS rows for
    that backend are exposed as selectable pairs. A minimal fallback keeps
    local development usable when the Linux-only dependency is not installed.
    """

    discovered_dir = matrix_dir or _discover_matrix_dir()
    if discovered_dir is not None:
        pairs = _read_pairs(discovered_dir, backend=backend)
        if pairs:
            version = package_version
            if version is None:
                try:
                    version = metadata.version("aiconfigurator")
                except metadata.PackageNotFoundError:
                    version = None
            return _build_matrix(
                pairs,
                backend=backend,
                source="installed-wheel",
                package_version=version,
            )

    return _build_matrix(
        (
            SupportPair(
                model="Qwen/Qwen3-32B-FP8",
                system="h200_sxm",
                status="PASS",
            ),
        ),
        backend=backend,
        source="fallback-default",
        package_version=None,
    )


def _discover_matrix_dir() -> Path | None:
    try:
        spec = find_spec("aiconfigurator_core")
    except (ImportError, ModuleNotFoundError, ValueError):
        return None
    if spec is None or not spec.submodule_search_locations:
        return None
    matrix_dir = (
        Path(next(iter(spec.submodule_search_locations)))
        / "systems"
        / "support_matrix"
    )
    return matrix_dir if matrix_dir.is_dir() else None


def _read_pairs(matrix_dir: Path, *, backend: str) -> tuple[SupportPair, ...]:
    best_status: dict[tuple[str, str], str] = {}
    for csv_path in sorted(matrix_dir.glob("*.csv")):
        try:
            with csv_path.open(newline="", encoding="utf-8") as handle:
                rows: Iterable[dict[str, str]] = csv.DictReader(handle)
                for row in rows:
                    row_backend = row.get("Backend", "").strip().lower()
                    status = row.get("Status", "").strip().upper()
                    model = row.get("HuggingFaceID", "").strip()
                    system = row.get("System", "").strip()
                    if (
                        row_backend != backend.lower()
                        or status not in SUPPORTED_STATUSES
                        or not model
                        or not system
                    ):
                        continue
                    key = (model, system)
                    previous = best_status.get(key)
                    if (
                        previous is None
                        or _STATUS_PRIORITY[status] > _STATUS_PRIORITY[previous]
                    ):
                        best_status[key] = status
        except (OSError, UnicodeError, csv.Error):
            continue

    return tuple(
        SupportPair(model=model, system=system, status=status)
        for (model, system), status in sorted(best_status.items())
    )


def _build_matrix(
    pairs: Iterable[SupportPair],
    *,
    backend: str,
    source: str,
    package_version: str | None,
) -> SupportMatrix:
    ordered_pairs = tuple(sorted(pairs, key=lambda pair: (pair.model, pair.system)))
    return SupportMatrix(
        backend=backend,
        source=source,
        aiconfigurator_version=package_version,
        models=tuple(sorted({pair.model for pair in ordered_pairs})),
        systems=tuple(sorted({pair.system for pair in ordered_pairs})),
        pairs=ordered_pairs,
    )
