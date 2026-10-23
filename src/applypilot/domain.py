"""Validated user configuration and independent workflow states."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def now() -> str:
    return datetime.now(UTC).isoformat()


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Status(StrEnum):
    PENDING = "Pending"
    NEEDS_USER = "Needs user"
    BLOCKED = "Blocked"
    SKIPPED = "Skipped"
    SUBMITTED = "Submitted"


class Fact(Record):
    value: str | bool | None = None
    scope: str = ""
    source: str = "user"
    confirmed_at: str = Field(default_factory=now)


class Rules(Record):
    excluded_titles: list[str] = Field(default_factory=list)
    excluded_companies: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    allow_remote: bool = True
    minimum_salary: float | None = Field(default=None, ge=0)
    salary_currency: str = "USD"
    salary_period: Literal["year", "month", "hour"] = "year"
    unknown_salary: Literal["allow", "review", "skip"] = "allow"
    max_age_days: int | None = Field(default=None, ge=1)


class Source(Record):
    kind: Literal["greenhouse", "lever", "remoteok", "adzuna"]
    board: str = ""
    region: str = "us"
    query: str = ""
    enabled: bool = True


class ModelSettings(Record):
    enabled: bool = False
    base_url: str = "http://127.0.0.1:11434/v1"
    model: str = ""
    api_key_env: str = "APPLYPILOT_MODEL_API_KEY"
    max_calls_per_run: int = Field(default=3, ge=1, le=20)


class Profile(Record):
    name: str = ""
    email: str = ""
    location: str = ""
    target_roles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    rules: Rules = Field(default_factory=Rules)
    facts: dict[str, Fact] = Field(default_factory=dict)
    sources: list[Source] = Field(default_factory=list)
    model: ModelSettings = Field(default_factory=ModelSettings)


class Job(Record):
    id: str = ""
    source: str = "manual"
    source_id: str = ""
    title: str = Field(min_length=1, max_length=300)
    company: str = Field(min_length=1, max_length=300)
    url: str
    location: str = ""
    description: str = Field(default="", max_length=200_000)
    salary_min: float | None = Field(default=None, ge=0)
    salary_max: float | None = Field(default=None, ge=0)
    currency: str = ""
    period: Literal["year", "month", "hour", ""] = ""
    posted_at: str | None = None
    remote: bool = False
    sponsorship: Literal["unknown", "available", "unavailable"] = "unknown"
    country: str = ""
    availability: Literal["open", "expired", "unknown"] = "unknown"
    availability_evidence: str = ""
    fetched_at: str = Field(default_factory=now)

    @field_validator("url")
    @classmethod
    def web_url(cls, value: str) -> str:
        from urllib.parse import urlsplit

        parsed = urlsplit(value)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username:
            raise ValueError("Use an HTTP or HTTPS job URL without embedded credentials.")
        return value


class Resume(Record):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    id: str = ""
    label: str = Field(min_length=1, max_length=160)
    roles: list[str] = Field(default_factory=list)
    text: str = Field(min_length=1, max_length=200_000)
    source_name: str = "pasted text"


class Assessment(Record):
    status: Status = Status.PENDING
    fit: Literal["High", "Medium", "Low", "Unrated"] = "Unrated"
    reasons: list[str] = Field(default_factory=list)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)


class StatusUpdate(Record):
    status: Status
    note: str = ""
    evidence: str = ""
    evidence_type: Literal["user_reported", "confirmation_page", "confirmation_email"] = (
        "user_reported"
    )


class Answer(Record):
    question: str = Field(min_length=1)
    text: str = Field(min_length=1)
    scope: str = ""
    source: Literal["user_confirmed", "resume_based_draft"] = "user_confirmed"
    resume_id: str | None = None
    confirmed_at: str = Field(default_factory=now)


class Question(Record):
    text: str = Field(min_length=1)
    scope: str = ""
    job_id: str | None = None


class Result(Record):
    data: dict[str, Any] = Field(default_factory=dict)
