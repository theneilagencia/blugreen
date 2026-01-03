from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class MetricCategory(str, Enum):
    """Category of quality metric."""

    CODE_QUALITY = "code_quality"
    SECURITY = "security"
    UX = "ux"
    UI = "ui"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"


class MetricStatus(str, Enum):
    """Status of a metric evaluation."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    NOT_APPLICABLE = "not_applicable"


class QualityMetricBase(SQLModel):
    """Base model for quality metrics."""

    project_id: int = Field(foreign_key="project.id", index=True)
    category: MetricCategory
    name: str = Field(index=True)
    description: Optional[str] = None
    value: float  # Metric value (0-100 scale)
    threshold: float = Field(default=70.0)  # Passing threshold
    status: MetricStatus
    details: Optional[str] = None  # JSON string with detailed results
    version: int = Field(default=1)  # For versioning metrics


class QualityMetric(QualityMetricBase, table=True):
    """Quality metric for a project."""

    id: Optional[int] = Field(default=None, primary_key=True)
    measured_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    measured_by: Optional[str] = None  # Agent or service that measured


class QualityMetricCreate(QualityMetricBase):
    """Schema for creating quality metrics."""

    pass


class QualityMetricRead(QualityMetricBase):
    """Schema for reading quality metrics."""

    id: int
    measured_at: datetime
    measured_by: Optional[str]


class QualityMetricSummary(SQLModel):
    """Summary of quality metrics for a project."""

    project_id: int
    total_metrics: int
    passed: int
    failed: int
    warnings: int
    overall_score: float
    categories: dict[str, dict[str, int]]  # Category -> {passed, failed, warnings}
    latest_measurement: datetime
