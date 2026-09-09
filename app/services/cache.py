from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import json
import os
from threading import Lock
from typing import Mapping

from app.domain.results import RankedResults
from app.domain.runs import RunRequest


DEFAULT_CACHE_SIZE = 16
DEFAULT_AICONFIGURATOR_VERSION = "0.11.0"
DEFAULT_RESULT_MODEL_VERSION = "results-v1"
DEFAULT_RUNNER_IMAGE_IDENTITY = "local-unversioned"


@dataclass(frozen=True)
class CacheIdentity:
    """Version inputs that invalidate deterministic result entries."""

    aiconfigurator_version: str
    result_model_version: str
    runner_image_identity: str

    @classmethod
    def from_environment(cls) -> "CacheIdentity":
        return cls(
            aiconfigurator_version=os.getenv(
                "AICONFIGURATOR_VERSION", DEFAULT_AICONFIGURATOR_VERSION
            ),
            result_model_version=os.getenv(
                "AICONFIGURATOR_RESULT_MODEL_VERSION",
                DEFAULT_RESULT_MODEL_VERSION,
            ),
            runner_image_identity=os.getenv(
                "AICONFIGURATOR_RUNNER_IMAGE_DIGEST",
                DEFAULT_RUNNER_IMAGE_IDENTITY,
            ),
        )


@dataclass(frozen=True)
class CachedRun:
    """Successful normalized output safe to restore into a new run."""

    results: RankedResults
    artifacts: Mapping[str, bytes]


def build_cache_key(request: RunRequest, identity: CacheIdentity) -> str:
    """Build a stable digest from request and all cache invalidation inputs."""

    payload = {
        "request": request.model_dump(mode="json"),
        "aiconfigurator_version": identity.aiconfigurator_version,
        "result_model_version": identity.result_model_version,
        "runner_image_identity": identity.runner_image_identity,
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class ResultCache:
    """A bounded, process-local LRU cache for successful portal runs."""

    def __init__(self, *, max_entries: int = DEFAULT_CACHE_SIZE) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self._max_entries = max_entries
        self._entries: OrderedDict[str, CachedRun] = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> CachedRun | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            self._entries.move_to_end(key)
            return _copy_entry(entry)

    def put(
        self,
        key: str,
        results: RankedResults,
        artifacts: Mapping[str, bytes],
    ) -> None:
        entry = CachedRun(
            results=results.model_copy(deep=True),
            artifacts=dict(artifacts),
        )
        with self._lock:
            self._entries[key] = entry
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)


def _copy_entry(entry: CachedRun) -> CachedRun:
    return CachedRun(
        results=entry.results.model_copy(deep=True),
        artifacts=dict(entry.artifacts),
    )
