from app.domain.results import RankedResults
from app.domain.runs import RunRequest
from app.services.cache import CacheIdentity, ResultCache, build_cache_key


def make_request() -> RunRequest:
    return RunRequest(
        model="Qwen/Qwen3-32B-FP8",
        system="h200_sxm",
        total_gpus=32,
        ttft=2000,
        tpot=30,
    )


def make_results() -> RankedResults:
    return RankedResults(
        model="Qwen/Qwen3-32B-FP8",
        ttft_target_ms=2000,
        tpot_target_ms=30,
        candidates=[],
    )


def test_cache_key_is_stable_and_identity_changes_invalidate() -> None:
    request = make_request()
    identity = CacheIdentity("0.11.0", "results-v1", "sha256:image-a")

    assert build_cache_key(request, identity) == build_cache_key(request, identity)
    assert build_cache_key(
        request, CacheIdentity("0.11.0", "results-v1", "sha256:image-b")
    ) != build_cache_key(request, identity)
    assert build_cache_key(
        request, CacheIdentity("0.11.1", "results-v1", "sha256:image-a")
    ) != build_cache_key(request, identity)
    assert build_cache_key(
        request, CacheIdentity("0.11.0", "results-v2", "sha256:image-a")
    ) != build_cache_key(request, identity)


def test_cache_is_bounded_lru() -> None:
    cache = ResultCache(max_entries=2)
    results = make_results()
    cache.put("first", results, {})
    cache.put("second", results, {})
    assert cache.get("first") is not None

    cache.put("third", results, {})

    assert cache.get("first") is not None
    assert cache.get("second") is None
    assert cache.get("third") is not None
