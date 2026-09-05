from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ResultMode = Literal["agg", "disagg"]


class RankedResult(BaseModel):
    """Stable portal fields derived from one AIConfigurator CSV row."""

    model_config = ConfigDict(extra="forbid")

    rank: int = Field(gt=0)
    mode: ResultMode
    source: str
    meets_sla: bool
    predicted_tokens_per_second: float
    predicted_tokens_per_second_per_gpu: float
    predicted_ttft_ms: float
    predicted_tpot_ms: float
    predicted_request_latency_ms: float
    total_gpus: int = Field(gt=0)
    concurrency: float
    backend: str
    system: str
    raw: dict[str, str]


class RankedResults(BaseModel):
    """All normalized candidates ranked for one portal request."""

    model_config = ConfigDict(extra="forbid")

    model: str
    ttft_target_ms: float = Field(gt=0)
    tpot_target_ms: float = Field(gt=0)
    candidates: list[RankedResult]
