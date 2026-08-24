"""Domain service for generating semantic developer hints and insights from Patterns & Data Flow in Python."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.data_flow import DataFlowSummaryReport
from pattern_detector.domain.detection import DetectionReport
from pattern_detector.domain.insights import (
    InsightCategory,
    InsightSeverity,
    InsightsReport,
    PatternInsight,
)
from pattern_detector.domain.value_objects import PatternType, SourceLocation


class PatternInsightsService:
    """Combines Design Pattern Detections with Data Flow graphs to generate Python coder hints."""

    def generate_insights(
        self,
        model: CodeModel,
        pattern_report: DetectionReport,
        data_flow_summary: DataFlowSummaryReport | None = None,
    ) -> InsightsReport:
        """Analyze pattern-data interactions and formulate actionable Python coder guidance."""
        insights: list[PatternInsight] = []
        project_path = pattern_report.project_path

        # 1. Inspect Mediator & Observer data flows
        self._analyze_mediator_insights(model, pattern_report, data_flow_summary, insights)

        # 2. Inspect Builder construction lifecycles
        self._analyze_builder_insights(model, pattern_report, insights)

        # 3. Inspect Template Method & Async Tasks
        self._analyze_template_method_and_async_insights(model, pattern_report, insights)

        # 4. Inspect Abstract Factory object creation
        self._analyze_abstract_factory_insights(model, pattern_report, insights)

        # 5. Inspect High Blast Radius / Data Flow Mutability
        if data_flow_summary:
            self._analyze_data_flow_reach_insights(data_flow_summary, insights)

        return InsightsReport(project_path=project_path, insights=insights)

    def _analyze_mediator_insights(
        self,
        model: CodeModel,
        pattern_report: DetectionReport,
        df_summary: DataFlowSummaryReport | None,
        out_insights: list[PatternInsight],
    ) -> None:
        mediator_detections = [
            d for d in pattern_report.detections if d.pattern_type in (PatternType.MEDIATOR, PatternType.OBSERVER)
        ]

        for det in mediator_detections:
            if self._is_observable_hub(det.target_name):
                self._analyze_mediator_item(det, df_summary, out_insights)

    def _is_observable_hub(self, target_cls: str) -> bool:
        keywords = ("Observable", "Event", "Subject", "Dispatcher", "Emitter")
        return any(k in target_cls for k in keywords)

    def _analyze_mediator_item(
        self,
        det: Any,
        df_summary: DataFlowSummaryReport | None,
        out_insights: list[PatternInsight],
    ) -> None:
        target_cls = det.target_name.split("::")[0]
        loc = det.primary_location

        stats = self._collect_mediator_df_stats(df_summary)
        out_insights.append(self._create_blast_radius_insight(det, target_cls, loc, stats))
        out_insights.append(self._create_mediator_thread_safety_insight(det, target_cls, loc))

    def _collect_mediator_df_stats(self, df_summary: DataFlowSummaryReport | None) -> tuple[int, int, list[str]]:
        if not df_summary:
            return 0, 0, []

        readers_count = 0
        writers_count = 0
        affected: list[str] = []
        for s in df_summary.summaries:
            if any(k in s.name for k in ("value", "state", "listeners", "subscribers", "handlers")):
                readers_count += len(s.readers)
                writers_count += len(s.writers)
                affected.extend(s.readers)
        return readers_count, writers_count, affected

    def _create_blast_radius_insight(
        self,
        det: Any,
        target_cls: str,
        loc: SourceLocation,
        stats: tuple[int, int, list[str]],
    ) -> PatternInsight:
        readers_count, writers_count, affected = stats
        return PatternInsight(
            target_pattern=det.pattern_type,
            target_name=target_cls,
            data_entity="state / payload (Reactive State)",
            severity=InsightSeverity.INFO,
            category=InsightCategory.DATA_FLOW_IMPACT,
            title=f"Reactive State Blast Radius in '{target_cls}'",
            description=(
                f"The payload inside '{target_cls}' is mutated across {max(1, writers_count)} methods "
                f"and directly propagates to {max(2, readers_count)} downstream listeners/subscribers."
            ),
            suggestion=(
                "Ensure that state updates are cohesive. When updating multiple dependent fields, "
                "consider batching notifications into an immutable dataclass or namedtuple to avoid cascading UI/event triggers."
            ),
            code_snippet=(
                "# Tip: Batch updates into an immutable dataclass\n"
                "from dataclasses import dataclass\n\n"
                "@dataclass(frozen=True)\n"
                "class FormState:\n"
                "    username: str\n"
                "    is_active: bool\n\n"
                "observable.set(FormState(username='Alice', is_active=True))"
            ),
            location=loc,
            affected_components=sorted(set(affected))[:5],
        )

    def _create_mediator_thread_safety_insight(
        self,
        det: Any,
        target_cls: str,
        loc: SourceLocation,
    ) -> PatternInsight:
        return PatternInsight(
            target_pattern=det.pattern_type,
            target_name=target_cls,
            data_entity="listeners (Callback Invocation)",
            severity=InsightSeverity.SUGGESTION,
            category=InsightCategory.THREAD_SAFETY,
            title=f"Thread & Async Safety for '{target_cls}' Callbacks",
            description=(
                f"Callbacks in '{target_cls}' notify subscribers synchronously. If events originate from "
                "background threads or asyncio tasks, concurrent iteration over listeners list can raise RuntimeError."
            ),
            suggestion=(
                "Use threading.Lock() or iterate over a shallow copy of listeners `list(self._listeners)` "
                "to prevent mutation during iteration."
            ),
            code_snippet=(
                "# Safe observer notification with defensive copy:\n"
                "def notify(self, event: Event) -> None:\n"
                "    with self._lock:\n"
                "        listeners_snapshot = list(self._listeners)\n"
                "    for listener in listeners_snapshot:\n"
                "        listener(event)"
            ),
            location=loc,
            affected_components=[],
        )

    def _analyze_builder_insights(
        self,
        model: CodeModel,
        pattern_report: DetectionReport,
        out_insights: list[PatternInsight],
    ) -> None:
        builder_detections = [d for d in pattern_report.detections if d.pattern_type == PatternType.BUILDER]

        for det in builder_detections:
            target = det.target_name
            loc = det.primary_location or SourceLocation(file_path="", line=1)

            out_insights.append(
                PatternInsight(
                    target_pattern=PatternType.BUILDER,
                    target_name=target,
                    data_entity="Constructed Product Instance",
                    severity=InsightSeverity.SUGGESTION,
                    category=InsightCategory.RESOURCE_LIFECYCLE,
                    title=f"Fluent Lifecycle & Build Termination in '{target}'",
                    description=(
                        f"Builder '{target}' configures attributes incrementally via method chaining. "
                        "Methods return `self` to support fluent API."
                    ),
                    suggestion=(
                        f"Always conclude '{target}' configuration with a terminal execution method "
                        "such as `.build()` or `.get_result()` to validate required invariants before returning the product."
                    ),
                    code_snippet=(
                        "# Recommended: Terminal build with validation\n"
                        "class QueryBuilder:\n"
                        "    def select(self, *cols: str) -> Self: ...\n"
                        "    def where(self, condition: str) -> Self: ...\n"
                        "    def build(self) -> Query:\n"
                        "        if not self._cols:\n"
                        "            raise ValueError('Columns must be specified')\n"
                        "        return Query(cols=self._cols, condition=self._cond)"
                    ),
                    location=loc,
                )
            )

    def _analyze_template_method_and_async_insights(
        self,
        model: CodeModel,
        pattern_report: DetectionReport,
        out_insights: list[PatternInsight],
    ) -> None:
        tmpl_detections = [d for d in pattern_report.detections if d.pattern_type == PatternType.TEMPLATE_METHOD]

        for det in tmpl_detections:
            target = det.target_name
            loc = det.primary_location or SourceLocation(file_path="", line=1)

            out_insights.append(
                PatternInsight(
                    target_pattern=PatternType.TEMPLATE_METHOD,
                    target_name=target,
                    data_entity="Algorithm Primitive Steps & Hooks",
                    severity=InsightSeverity.INFO,
                    category=InsightCategory.ARCHITECTURAL_HEALTH,
                    title=f"Template Algorithm Extensibility in '{target}'",
                    description=(
                        f"Class '{target}' defines the skeleton of an algorithm in a template method, "
                        "deferring specific steps to subclasses."
                    ),
                    suggestion=(
                        "Mark primitive step methods with @abstractmethod or provide default hook implementations "
                        "to prevent subclasses from altering the algorithm execution order."
                    ),
                    code_snippet=(
                        "from abc import ABC, abstractmethod\n\n"
                        "class DataProcessor(ABC):\n"
                        "    def process(self) -> None:  # Template Method\n"
                        "        data = self.read_data()\n"
                        "        cleaned = self.transform(data)\n"
                        "        self.save(cleaned)\n\n"
                        "    @abstractmethod\n"
                        "    def transform(self, data: RawData) -> CleanData: ..."
                    ),
                    location=loc,
                )
            )

    def _analyze_abstract_factory_insights(
        self,
        model: CodeModel,
        pattern_report: DetectionReport,
        out_insights: list[PatternInsight],
    ) -> None:
        factory_detections = [d for d in pattern_report.detections if d.pattern_type == PatternType.ABSTRACT_FACTORY]

        for det in factory_detections:
            target = det.target_name
            loc = det.primary_location or SourceLocation(file_path="", line=1)

            out_insights.append(
                PatternInsight(
                    target_pattern=PatternType.ABSTRACT_FACTORY,
                    target_name=target,
                    data_entity="Product Family Protocols (typing.Protocol / ABC)",
                    severity=InsightSeverity.INFO,
                    category=InsightCategory.ARCHITECTURAL_HEALTH,
                    title=f"Protocol Typing in Factory '{target}'",
                    description=(
                        f"Factory '{target}' declares a family of creation methods. "
                        "In modern Python, using typing.Protocol enables structural subtyping (duck typing) without explicit inheritance."
                    ),
                    suggestion=(
                        "Return Protocol types from factory methods so callers depend strictly on behavioral interfaces."
                    ),
                    code_snippet=(
                        "from typing import Protocol\n\n"
                        "class UIFactory(Protocol):\n"
                        "    def create_button(self) -> Button: ...\n"
                        "    def create_dialog(self) -> Dialog: ..."
                    ),
                    location=loc,
                )
            )

    def _analyze_data_flow_reach_insights(
        self,
        df_summary: DataFlowSummaryReport,
        out_insights: list[PatternInsight],
    ) -> None:
        # Find high-impact variables (downstream reach >= 4)
        for s in df_summary.summaries:
            if s.downstream_reach >= 4 and len(s.writers) >= 2:
                loc = SourceLocation(file_path=s.file_path, line=s.line)
                clean_var = s.name.replace("self.", "")
                out_insights.append(
                    PatternInsight(
                        target_pattern=PatternType.MEDIATOR,
                        target_name=s.name,
                        data_entity=f"Variable '{s.name}'",
                        severity=InsightSeverity.WARNING,
                        category=InsightCategory.DATA_FLOW_IMPACT,
                        title=f"High Blast Radius Variable '{s.name}' (Reach: {s.downstream_reach})",
                        description=(
                            f"Variable '{s.name}' is mutated by {len(s.writers)} functions and read by {len(s.readers)} functions, "
                            f"reaching {s.downstream_reach} downstream elements."
                        ),
                        suggestion=(
                            f"Because '{s.name}' has a large blast radius, encapsulate it using a `@property` "
                            "or wrap it inside a dedicated state holder to prevent unintended side effects."
                        ),
                        code_snippet=(
                            "# Refactoring suggestion:\n"
                            "class StateHolder:\n"
                            "    def __init__(self) -> None:\n"
                            f"        self._{clean_var}: Any = None\n\n"
                            "    @property\n"
                            f"    def {clean_var}(self) -> Any:\n"
                            f"        return self._{clean_var}"
                        ),
                        location=loc,
                        affected_components=s.readers[:4],
                    )
                )
