"""
API endpoints for quality metrics.

Provides endpoints for:
- Recording quality metrics for projects
- Retrieving metrics history
- Getting metric summaries
- Comparing metrics across versions
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, func, select

from app.database import get_session
from app.models.project import Project
from app.models.quality_metric import (
    MetricCategory,
    MetricStatus,
    QualityMetric,
    QualityMetricCreate,
    QualityMetricRead,
    QualityMetricSummary,
)

router = APIRouter(prefix="/projects/{project_id}/metrics", tags=["metrics"])


@router.post("/", response_model=QualityMetricRead)
def record_metric(
    project_id: int,
    metric: QualityMetricCreate,
    session: Session = Depends(get_session),
) -> QualityMetric:
    """Record a new quality metric for a project."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Auto-determine status based on value and threshold
    if metric.status is None:
        if metric.value >= metric.threshold:
            metric.status = MetricStatus.PASSED
        elif metric.value >= metric.threshold * 0.8:
            metric.status = MetricStatus.WARNING
        else:
            metric.status = MetricStatus.FAILED

    db_metric = QualityMetric.model_validate(metric)
    db_metric.project_id = project_id
    session.add(db_metric)
    session.commit()
    session.refresh(db_metric)

    return db_metric


@router.get("/", response_model=list[QualityMetricRead])
def list_metrics(
    project_id: int,
    category: Optional[MetricCategory] = None,
    status: Optional[MetricStatus] = None,
    days: int = Query(default=30, ge=1, le=365),
    session: Session = Depends(get_session),
) -> list[QualityMetric]:
    """List quality metrics for a project with optional filters."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = select(QualityMetric).where(
        QualityMetric.project_id == project_id,
        QualityMetric.measured_at >= cutoff_date,
    )

    if category:
        query = query.where(QualityMetric.category == category)

    if status:
        query = query.where(QualityMetric.status == status)

    query = query.order_by(QualityMetric.measured_at.desc())

    return list(session.exec(query).all())


@router.get("/summary", response_model=QualityMetricSummary)
def get_metrics_summary(
    project_id: int,
    days: int = Query(default=30, ge=1, le=365),
    session: Session = Depends(get_session),
) -> QualityMetricSummary:
    """Get a summary of quality metrics for a project."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Get all metrics within the time range
    metrics = session.exec(
        select(QualityMetric).where(
            QualityMetric.project_id == project_id,
            QualityMetric.measured_at >= cutoff_date,
        )
    ).all()

    if not metrics:
        raise HTTPException(
            status_code=404,
            detail="No metrics found for this project in the specified time range",
        )

    # Calculate summary
    total = len(metrics)
    passed = sum(1 for m in metrics if m.status == MetricStatus.PASSED)
    failed = sum(1 for m in metrics if m.status == MetricStatus.FAILED)
    warnings = sum(1 for m in metrics if m.status == MetricStatus.WARNING)

    # Calculate overall score (average of all metric values)
    overall_score = sum(m.value for m in metrics) / total if total > 0 else 0

    # Group by category
    categories: dict[str, dict[str, int]] = {}
    for metric in metrics:
        cat = metric.category.value
        if cat not in categories:
            categories[cat] = {"passed": 0, "failed": 0, "warnings": 0}

        if metric.status == MetricStatus.PASSED:
            categories[cat]["passed"] += 1
        elif metric.status == MetricStatus.FAILED:
            categories[cat]["failed"] += 1
        elif metric.status == MetricStatus.WARNING:
            categories[cat]["warnings"] += 1

    # Get latest measurement time
    latest = max(m.measured_at for m in metrics)

    return QualityMetricSummary(
        project_id=project_id,
        total_metrics=total,
        passed=passed,
        failed=failed,
        warnings=warnings,
        overall_score=round(overall_score, 2),
        categories=categories,
        latest_measurement=latest,
    )


@router.get("/latest", response_model=list[QualityMetricRead])
def get_latest_metrics(
    project_id: int,
    session: Session = Depends(get_session),
) -> list[QualityMetric]:
    """Get the latest version of each metric for a project."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get the latest metric for each (category, name) combination
    subquery = (
        select(
            QualityMetric.category,
            QualityMetric.name,
            func.max(QualityMetric.version).label("max_version"),
        )
        .where(QualityMetric.project_id == project_id)
        .group_by(QualityMetric.category, QualityMetric.name)
        .subquery()
    )

    query = (
        select(QualityMetric)
        .join(
            subquery,
            (QualityMetric.category == subquery.c.category)
            & (QualityMetric.name == subquery.c.name)
            & (QualityMetric.version == subquery.c.max_version),
        )
        .where(QualityMetric.project_id == project_id)
    )

    return list(session.exec(query).all())


@router.get("/history/{metric_name}", response_model=list[QualityMetricRead])
def get_metric_history(
    project_id: int,
    metric_name: str,
    category: MetricCategory,
    days: int = Query(default=30, ge=1, le=365),
    session: Session = Depends(get_session),
) -> list[QualityMetric]:
    """Get the history of a specific metric."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = (
        select(QualityMetric)
        .where(
            QualityMetric.project_id == project_id,
            QualityMetric.name == metric_name,
            QualityMetric.category == category,
            QualityMetric.measured_at >= cutoff_date,
        )
        .order_by(QualityMetric.measured_at.desc())
    )

    return list(session.exec(query).all())


@router.get("/categories")
def get_metric_categories() -> list[dict[str, str]]:
    """Get all available metric categories."""
    return [
        {
            "value": MetricCategory.CODE_QUALITY.value,
            "label": "Code Quality",
            "description": "Metrics related to code structure, maintainability, and best practices",
        },
        {
            "value": MetricCategory.SECURITY.value,
            "label": "Security",
            "description": "Metrics related to security vulnerabilities and best practices",
        },
        {
            "value": MetricCategory.UX.value,
            "label": "User Experience",
            "description": "Metrics related to user experience and usability",
        },
        {
            "value": MetricCategory.UI.value,
            "label": "User Interface",
            "description": "Metrics related to visual design and interface quality",
        },
        {
            "value": MetricCategory.PERFORMANCE.value,
            "label": "Performance",
            "description": "Metrics related to application performance and optimization",
        },
        {
            "value": MetricCategory.ARCHITECTURE.value,
            "label": "Architecture",
            "description": "Metrics related to system architecture and design patterns",
        },
    ]


@router.delete("/{metric_id}")
def delete_metric(
    project_id: int,
    metric_id: int,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """Delete a quality metric."""
    metric = session.get(QualityMetric, metric_id)

    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    if metric.project_id != project_id:
        raise HTTPException(
            status_code=403,
            detail="Metric does not belong to this project",
        )

    session.delete(metric)
    session.commit()

    return {"message": "Metric deleted"}
