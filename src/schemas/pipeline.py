from __future__ import annotations

from pydantic import BaseModel


class ArtifactStatus(BaseModel):
    name: str
    path: str
    exists: bool
    readable: bool | None = None
    row_count: int | None = None
    latest_timestamp: str | None = None
    error: str | None = None


class StageStatus(BaseModel):
    stage: str
    artifacts: list[ArtifactStatus]


class PipelineStatusResponse(BaseModel):
    symbol: str
    timeframe: str
    generated_at: str
    stages: list[StageStatus]
