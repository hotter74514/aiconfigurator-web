from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.results import RankedResults


class RunRequest(BaseModel):
    """User-supplied constraints accepted by POST /api/runs."""

    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1)
    system: str = Field(min_length=1)
    total_gpus: int = Field(gt=0)
    ttft: float = Field(gt=0)
    tpot: float = Field(gt=0)

    @field_validator("model", "system", mode="before")
    @classmethod
    def strip_required_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


RunStatus = Literal["queued", "running", "completed", "failed"]


class RunAcceptedResponse(BaseModel):
    id: UUID
    status: Literal["queued"]


class RunStatusResponse(BaseModel):
    id: UUID
    status: RunStatus
    error: str | None = None
    results: RankedResults | None = None
    artifacts: list[str] | None = None


class RunHistoryItem(BaseModel):
    """A recent terminal run exposed by the process-local history API."""

    id: UUID
    status: Literal["completed", "failed"]
    request: RunRequest
    created_at: datetime
    error: str | None = None
    results: RankedResults | None = None
    artifacts: list[str] = Field(default_factory=list)
    artifacts_unavailable: bool = False


class StoredRun(BaseModel):
    id: UUID
    request: RunRequest
    status: RunStatus
    created_at: datetime
    error: str | None = None
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration_ms: int | None = None
    results: RankedResults | None = None
    artifacts: list[str] = Field(default_factory=list)


def new_stored_run(request: RunRequest) -> StoredRun:
    return StoredRun(
        id=uuid4(),
        request=request,
        status="queued",
        created_at=datetime.now(timezone.utc),
    )
