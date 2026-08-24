"""Domain Value Objects and Models for Pattern & Data Flow Semantic Insights."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from pattern_detector.domain.value_objects import PatternType, SourceLocation


class InsightCategory(str, Enum):
    """Categorization of semantic developer insights."""

    DATA_FLOW_IMPACT = "data_flow_impact"
    THREAD_SAFETY = "thread_safety"
    RESOURCE_LIFECYCLE = "resource_lifecycle"
    ARCHITECTURAL_HEALTH = "architectural_health"
    INVARIANT_RISK = "invariant_risk"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"


class InsightSeverity(str, Enum):
    """Severity level of an insight/suggestion."""

    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    SUGGESTION = "SUGGESTION"
    INFO = "INFO"


@dataclass
class PatternInsight:
    """Actionable semantic hint/insight connecting a Design Pattern with its Data Flow."""

    target_pattern: PatternType
    target_name: str
    data_entity: str
    severity: InsightSeverity
    category: InsightCategory
    title: str
    description: str
    suggestion: str
    code_snippet: str | None = None
    location: SourceLocation | None = None
    affected_components: list[str] = field(default_factory=list)


@dataclass
class InsightsReport:
    """Collection of semantic insights generated for a codebase."""

    project_path: str
    insights: list[PatternInsight] = field(default_factory=list)

    @property
    def total_insights(self) -> int:
        return len(self.insights)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.insights if i.severity == InsightSeverity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.insights if i.severity == InsightSeverity.WARNING)

    @property
    def suggestion_count(self) -> int:
        return sum(1 for i in self.insights if i.severity == InsightSeverity.SUGGESTION)
