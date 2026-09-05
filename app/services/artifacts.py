from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
import time
from uuid import UUID


ALLOWED_ARTIFACT_FILENAMES = frozenset(
    {
        "agg_config.yaml",
        "best_config_topn.csv",
        "bench_run.sh",
        "decode_config.yaml",
        "exp_config.yaml",
        "generator_config.yaml",
        "k8s_bench.yaml",
        "k8s_deploy.yaml",
        "pareto.csv",
        "pareto_frontier.png",
        "per_ops_source.json",
        "prefill_config.yaml",
        "sflow.yaml",
    }
)
RUN_SCRIPT_PATTERN = re.compile(r"run_[0-9]+\.sh\Z")
DEFAULT_TTL_SECONDS = 24 * 60 * 60


class ArtifactNotFoundError(LookupError):
    """Raised when a requested artifact is absent or not allow-listed."""


class ArtifactStoreError(RuntimeError):
    """Raised when an artifact directory cannot be inspected safely."""


class ArtifactStore:
    """Manage ephemeral per-run artifacts and enforce download boundaries."""

    def __init__(
        self, root: Path | str, *, ttl_seconds: int = DEFAULT_TTL_SECONDS
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.root = Path(root)
        self.ttl_seconds = ttl_seconds

    def prepare_run(self, run_id: UUID) -> Path:
        run_dir = self.run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def cleanup_expired(self, *, now: float | None = None) -> None:
        """Remove only UUID-named run directories older than the TTL."""

        if not self.root.is_dir():
            return
        current_time = time.time() if now is None else now
        for child in self.root.iterdir():
            if not child.is_dir():
                continue
            try:
                UUID(child.name)
                age_seconds = current_time - child.stat().st_mtime
            except (OSError, ValueError):
                continue
            if age_seconds > self.ttl_seconds:
                shutil.rmtree(child, ignore_errors=True)

    def run_dir(self, run_id: UUID) -> Path:
        return self.root / str(run_id)

    def remove_run(self, run_id: UUID) -> None:
        shutil.rmtree(self.run_dir(run_id), ignore_errors=True)

    def is_writable(self) -> bool:
        """Return whether the artifact root can create and remove a file."""

        try:
            self.root.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=self.root, prefix=".readiness-", delete=True
            ):
                pass
        except OSError:
            return False
        return True

    def find_result_root(self, run_id: UUID) -> Path:
        run_dir = self.run_dir(run_id)
        roots = {
            path.parent.parent
            for path in run_dir.rglob("best_config_topn.csv")
            if path.parent.name in {"agg", "disagg"}
            and _is_within(path, run_dir)
        }
        if len(roots) != 1:
            raise ArtifactStoreError(
                f"Expected one AIConfigurator result root for run {run_id}, "
                f"found {len(roots)}"
            )
        return roots.pop()

    def list_allowed(self, run_id: UUID) -> list[str]:
        run_dir = self.run_dir(run_id)
        if not run_dir.is_dir():
            return []
        allowed: list[str] = []
        for path in run_dir.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(run_dir)
            if not self._is_allowed_relative(relative):
                continue
            try:
                resolved = path.resolve()
                resolved.relative_to(run_dir.resolve())
            except ValueError:
                continue
            allowed.append(relative.as_posix())
        return sorted(allowed)

    def total_allowed_bytes(self, run_id: UUID) -> int:
        """Return the size of all allow-listed files in a run directory."""

        total = 0
        for name in self.list_allowed(run_id):
            try:
                total += self.resolve_allowed(run_id, name).stat().st_size
            except OSError:
                continue
        return total

    def resolve_allowed(self, run_id: UUID, name: str) -> Path:
        relative = self._parse_relative_name(name)
        run_dir = self.run_dir(run_id)
        if not self._is_allowed_relative(relative):
            raise ArtifactNotFoundError(name)

        path = run_dir.joinpath(*relative.parts)
        try:
            resolved = path.resolve()
            resolved.relative_to(run_dir.resolve())
        except ValueError as exc:
            raise ArtifactNotFoundError(name) from exc
        if not resolved.is_file():
            raise ArtifactNotFoundError(name)
        return resolved

    def _is_allowed_relative(self, relative: PurePosixPath) -> bool:
        return relative.name in ALLOWED_ARTIFACT_FILENAMES or bool(
            RUN_SCRIPT_PATTERN.fullmatch(relative.name)
        )

    @staticmethod
    def _parse_relative_name(name: str) -> PurePosixPath:
        if not name or "\\" in name:
            raise ArtifactNotFoundError(name)
        relative = PurePosixPath(name)
        if relative.is_absolute() or any(
            part in {"", ".", ".."} for part in relative.parts
        ):
            raise ArtifactNotFoundError(name)
        return relative


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True
