"""Open/Closed Principle (OCP) Detection Rule for Python."""

from __future__ import annotations

import re
from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternCategory, PatternType

_ISINSTANCE_RE = re.compile(r"\bisinstance\s*\(\s*[^,]+,\s*([A-Za-z0-9_]+)\s*\)")
_TYPE_CHECK_RE = re.compile(r"\btype\s*\([^)]+\)\s*(?:is|==)\s*([A-Za-z0-9_]+)")
_DYNAMIC_CAST_RE = re.compile(r"\bdynamic_cast\s*<\s*([A-Za-z0-9_:]+)\s*[\*&]\s*>\s*\(")


class OpenClosedPrincipleRule(BasePatternRule):
    """Detects violations and adherences to the Open/Closed Principle (OCP) in Python.

    Indicators:
    - OCP Violation (Type-testing cascade): Method body containing cascades of `isinstance` / `type()` checks
      instead of polymorphic dispatch / Protocol methods.
    - OCP Adherence: Extensible polymorphic Protocol/ABC design with clean implementations.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.OPEN_CLOSED

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        detections.extend(self._detect_type_check_violations(model))
        detections.extend(self._detect_polymorphic_hierarchies(model))
        return detections

    def _detect_type_check_violations(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        for fn in model.all_functions():
            detection = self._analyze_function_type_checks(fn)
            if detection:
                detections.append(detection)
        return detections

    def _analyze_function_type_checks(self, fn: Any) -> Detection | None:
        if self.is_test_entity(fn):
            return None
        simple_name = fn.name.split(".")[-1]
        if simple_name in ("__eq__", "__ne__", "__lt__", "__gt__", "__le__", "__ge__", "__init__"):
            return None

        body = fn.body_text or ""
        isinstance_matches = _ISINSTANCE_RE.findall(body)
        type_matches = _TYPE_CHECK_RE.findall(body)
        cast_matches = _DYNAMIC_CAST_RE.findall(body)
        total_type_checks = len(isinstance_matches) + len(type_matches) + len(cast_matches)

        if total_type_checks < 2:
            return None

        all_types = isinstance_matches + type_matches + cast_matches
        types_str = ", ".join(all_types[:4])
        evidences: list[Evidence] = [
            self.evidence(
                description=f"Function/Method '{fn.name}' performs explicit type inspection ({types_str}) using isinstance cascades, violating OCP",
                weight=min(0.65, 0.40 + 0.10 * total_type_checks),
                location=fn.location,
                code_suffix="OCP_TYPE_CHECK_CASCADE",
            ),
            self.evidence(
                description="Adding new types requires modifying this function rather than extending via polymorphic dispatch",
                weight=0.35,
                location=fn.location,
                code_suffix="OCP_FRAGILE_MODIFICATION",
            ),
        ]

        detection = self.create_detection(
            target_name=fn.name,
            target_kind="ocp_type_check_violation",
            evidences=evidences,
            primary_location=fn.location,
            summary=f"OCP Violation: '{fn.name}' uses {total_type_checks} isinstance/type checks instead of polymorphic dispatch",
            base_score=0.35,
        )
        detection.pattern_category = PatternCategory.PRINCIPLE
        return detection

    def _detect_polymorphic_hierarchies(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        for proto in model.all_protocols():
            implementing_classes = model.find_records_implementing(proto.name)
            if len(implementing_classes) < 2:
                continue

            impl_names = ", ".join(r.name for r in implementing_classes[:4])
            evidences = [
                self.evidence(
                    description=f"Abstract interface/Protocol '{proto.name}' enables open extension through {len(implementing_classes)} polymorphic implementations: {impl_names}",
                    weight=min(0.70, 0.40 + 0.10 * len(implementing_classes)),
                    location=proto.location,
                    code_suffix="OCP_POLYMORPHIC_ABSTRACTION",
                ),
                self.evidence(
                    description="New behaviors can be added by implementing the Protocol/ABC without modifying existing consumers",
                    weight=0.35,
                    location=proto.location,
                    code_suffix="OCP_EXTENSIBLE_DESIGN",
                ),
            ]

            detection = self.create_detection(
                target_name=proto.name,
                target_kind="ocp_polymorphic_hierarchy",
                evidences=evidences,
                primary_location=proto.location,
                related_locations=[r.location for r in implementing_classes],
                summary=f"OCP Adherence: Interface '{proto.name}' supports open extension with {len(implementing_classes)} implementations",
                base_score=0.35,
            )
            detection.pattern_category = PatternCategory.PRINCIPLE
            detections.append(detection)

        return detections
