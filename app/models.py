from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class BestMatchPayload(BaseModel):
    key: str | None = None
    name: str | None = None
    percentage: float | None = None


class ResultPayload(BaseModel):
    attemptId: str = Field(min_length=1)
    quizVersion: str = "unknown"
    totalQuestions: int = Field(gt=0)
    answers: list[int]
    bestMatch: BestMatchPayload | None = None
    topThree: list[dict[str, Any]] = Field(default_factory=list)
    scores: dict[str, Any] = Field(default_factory=dict)
    submittedAt: datetime = Field(default_factory=lambda: datetime.now(UTC))
    pagePath: str = ""
    pageUrl: str = ""
    userAgent: str = ""
    region: str | None = None
    regionCode: str | None = None
    city: str | None = None

    @field_validator("attemptId")
    @classmethod
    def validate_attempt_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Missing attemptId")
        return normalized

    @field_validator("quizVersion")
    @classmethod
    def validate_quiz_version(cls, value: str) -> str:
        return value.strip() or "unknown"

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, value: list[int], info) -> list[int]:
        total_questions = info.data.get("totalQuestions")
        if total_questions and len(value) != total_questions:
            raise ValueError("Answers length does not match totalQuestions")
        return value
