"""
Space Operations Co-Pilot — Evaluation & QA Data Models.

Pydantic v2 models for assertion results, rubric scoring,
and composite evaluation outcomes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, computed_field


class Assertion(BaseModel):
    """A single evaluation assertion against a pipeline output."""

    type: str = Field(..., description="Assertion type (field_equals, field_exists, etc.)")
    path: str = Field(..., description="JSONPath to the field under test")
    value: Optional[Any] = Field(None, description="Expected value (for equality checks)")
    min: Optional[float] = Field(None, description="Minimum bound (for range checks)")
    max: Optional[float] = Field(None, description="Maximum bound (for range checks)")
    substring: Optional[str] = Field(None, description="Expected substring (for contains checks)")
    message: Optional[str] = Field(None, description="Human-readable assertion description")
    result: Optional[bool] = Field(None, description="True=pass, False=fail, None=not yet run")


class CriterionResult(BaseModel):
    """Result of evaluating a single rubric criterion."""

    criterion_id: str = Field(..., description="Criterion identifier (e.g., ACC-01)")
    description: str = Field(..., description="What this criterion measures")
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight within its rubric")
    score: float = Field(..., ge=0.0, le=1.0, description="Score achieved (0.0-1.0)")
    is_critical_fail: bool = Field(
        default=False, description="Whether this is a critical (zero-score) failure"
    )
    evidence: Optional[str] = Field(None, description="Evidence or reason for score")


class RubricResult(BaseModel):
    """Result of evaluating a complete rubric (e.g., Accuracy, Guardrails)."""

    name: str = Field(..., description="Rubric name")
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight in composite score")
    criteria: list[CriterionResult] = Field(
        default_factory=list, description="Individual criterion results"
    )

    @computed_field
    @property
    def score(self) -> float:
        """Weighted average score across all criteria in this rubric."""
        if not self.criteria:
            return 0.0
        total_weight = sum(c.weight for c in self.criteria)
        if total_weight == 0:
            return 0.0
        return sum(c.score * c.weight for c in self.criteria) / total_weight


class EvaluationResult(BaseModel):
    """Complete evaluation suite result with composite scoring."""

    suite_name: str = Field(
        default="Space Operations Co-Pilot Evaluation",
        description="Evaluation suite identifier",
    )
    timestamp: datetime = Field(
        ..., description="Evaluation run timestamp (UTC)"
    )
    rubrics: list[RubricResult] = Field(
        default_factory=list, description="Individual rubric results"
    )

    @computed_field
    @property
    def composite_score(self) -> float:
        """Weighted composite score across all rubrics."""
        if not self.rubrics:
            return 0.0
        total_weight = sum(r.weight for r in self.rubrics)
        if total_weight == 0:
            return 0.0
        return sum(r.score * r.weight for r in self.rubrics) / total_weight

    @computed_field
    @property
    def critical_failures(self) -> list[str]:
        """List of criterion IDs that are critical failures."""
        failures = []
        for rubric in self.rubrics:
            for criterion in rubric.criteria:
                if criterion.is_critical_fail:
                    failures.append(criterion.criterion_id)
        return failures

    @computed_field
    @property
    def is_pass(self) -> bool:
        """Whether the evaluation passes (≥0.80 and no critical failures)."""
        return self.composite_score >= 0.80 and len(self.critical_failures) == 0
