"""Composition Over Inheritance Principle Detection Rule."""

from __future__ import annotations

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import PatternCategory, PatternType


class CompositionOverInheritanceRule(BasePatternRule):
    """Detects deep inheritance hierarchies violating Composition Over Inheritance vs clean delegation.

    Indicators:
    - Deep Inheritance Chain (Depth >= 3): Class hierarchy where A extends B extends C extends D.
    - Composition / Delegation Adherence: Class encapsulating wrapped components via fields.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.COMPOSITION_OVER_INHERITANCE

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        records_by_name = {r.name: r for r in model.all_records()}

        # 1. Compute inheritance chain depth for each class
        def get_inheritance_depth(name: str, visited: set[str]) -> list[str]:
            if name in visited or name not in records_by_name:
                return [name]
            visited.add(name)
            rec = records_by_name[name]
            # Check superclasses in implemented_protocols
            for parent in rec.implemented_protocols:
                if parent in records_by_name:
                    return [name] + get_inheritance_depth(parent, visited)
            return [name]

        for rec in model.all_records():
            chain = get_inheritance_depth(rec.name, set())
            depth = len(chain) - 1

            if depth >= 3:
                chain_str = " -> ".join(chain)
                evidences = [
                    self.evidence(
                        description=f"Class '{rec.name}' has excessive inheritance depth of {depth} ({chain_str}), violating Composition Over Inheritance",
                        weight=min(0.70, 0.40 + 0.10 * depth),
                        location=rec.location,
                        code_suffix="DEEP_INHERITANCE_HIERARCHY",
                    ),
                    self.evidence(
                        description="Deep inheritance trees create tight compile-time coupling and fragile base class vulnerabilities",
                        weight=0.35,
                        location=rec.location,
                        code_suffix="FRAGILE_BASE_CLASS_RISK",
                    ),
                ]

                detection = self.create_detection(
                    target_name=rec.name,
                    target_kind="deep_inheritance_tree",
                    evidences=evidences,
                    primary_location=rec.location,
                    summary=f"Deep Inheritance Hierarchy (Depth {depth}): '{rec.name}' ({chain_str}); prefer composition",
                    base_score=0.40,
                )
                detection.pattern_category = PatternCategory.PRINCIPLE
                detections.append(detection)

        return detections
