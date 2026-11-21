from typing import Any, Literal

from pydantic import BaseModel, Field


class EvaluatePreviewRequest(BaseModel):
    request_id: str | None = None
    profile_key: str | None = None
    draft_rules: dict[str, dict[str, Any]] | None = None
    candidate_ids: list[int] = Field(default_factory=list, max_length=100)
    recommendation_filter: Literal["review", "exclude"] | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class CreateEvaluationRequest(BaseModel):
    profile_key: str | None = None
    draft_rules: dict[str, dict[str, Any]] | None = None


class ProfileUpdateRequest(BaseModel):
    config: dict[str, Any]


class ReviewRequest(BaseModel):
    candidate_id: int
    decision: str
    note: str | None = None


class ExportRequest(BaseModel):
    evaluation_id: int = Field(ge=1)
