"""High Cohesion and Low Coupling Principle Detection Rule."""

from __future__ import annotations

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import PatternCategory, PatternType, SourceLocation


class CohesionCouplingRule(BasePatternRule):
    """Detects tight coupling (high fan-out / CBO) and low cohesion metrics.

    Indicators:
    - High Efferent Coupling (Fan-Out): Package depending on >= 4 distinct internal packages.
    - Highly cohesive modular packages and components.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.HIGH_COHESION_LOW_COUPLING

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        graph = model.build_namespace_dependency_graph()

        # Analyze namespace/package coupling
        for ns in model.namespaces.values():
            deps = sorted(graph.get(ns.name, set()))

            if len(deps) >= 4:
                deps_str = ", ".join(deps)
                loc = SourceLocation(file_path=ns.file_path, line=1, column=1)
                evidences = [
                    self.evidence(
                        description=f"Package '{ns.name}' has high efferent coupling (Fan-Out = {len(deps)}), depending on: {deps_str}",
                        weight=min(0.65, 0.35 + 0.08 * len(deps)),
                        location=loc,
                        code_suffix="HIGH_EFFERENT_COUPLING",
                    ),
                    self.evidence(
                        description="High fan-out coupling increases regression risks when changing dependent modules",
                        weight=0.30,
                        location=loc,
                        code_suffix="TIGHT_MODULE_COUPLING",
                    ),
                ]

                detection = self.create_detection(
                    target_name=ns.name,
                    target_kind="high_coupling_module",
                    evidences=evidences,
                    primary_location=loc,
                    summary=f"Tight Coupling (Fan-Out {len(deps)}): Package '{ns.name}' depends on {len(deps)} other modules",
                    base_score=0.35,
                )
                detection.pattern_category = PatternCategory.PRINCIPLE
                detections.append(detection)

        return detections
