"""Interface Segregation Principle (ISP) Detection Rule."""

from __future__ import annotations

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import PatternCategory, PatternType


class InterfaceSegregationRule(BasePatternRule):
    """Detects violations (Fat Interfaces) and good practices (Role Interfaces) for ISP.

    Indicators:
    - ISP Violation (Fat Interface): Interface with > 8 methods forcing clients to implement
      unnecessary methods.
    - ISP Adherence (Fine-Grained Role Interface): Focused role interface with 1-3 cohesive methods.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.INTERFACE_SEGREGATION

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []

        for proto in model.all_protocols():
            method_count = len(proto.methods)

            # 1. Fat Interface Violation (>7 methods)
            if method_count >= 8:
                method_names_str = ", ".join(m.name for m in proto.methods[:6]) + ("..." if method_count > 6 else "")
                evidences = [
                    self.evidence(
                        description=f"Interface '{proto.name}' is a Fat Interface defining {method_count} methods ({method_names_str}), violating ISP",
                        weight=min(0.65, 0.35 + 0.04 * method_count),
                        location=proto.location,
                        code_suffix="ISP_FAT_INTERFACE",
                    ),
                    self.evidence(
                        description="Clients and implementors are forced to depend on methods they may not use",
                        weight=0.35,
                        location=proto.location,
                        code_suffix="ISP_UNNEEDED_DEPENDENCY",
                    ),
                ]

                detection = self.create_detection(
                    target_name=proto.name,
                    target_kind="fat_interface_isp_violation",
                    evidences=evidences,
                    primary_location=proto.location,
                    summary=f"ISP Violation (Fat Interface): '{proto.name}' has {method_count} methods; should be split into smaller role interfaces",
                    base_score=0.40,
                )
                detection.pattern_category = PatternCategory.PRINCIPLE
                detections.append(detection)

            # 2. Fine-Grained Role Interface Adherence (1 to 3 methods with implementing classes)
            elif 1 <= method_count <= 3:
                rec_impls = model.find_records_implementing(proto.name)
                if len(rec_impls) >= 2:
                    evidences = [
                        self.evidence(
                            description=f"Interface '{proto.name}' follows ISP as a cohesive role interface with only {method_count} method(s)",
                            weight=0.50,
                            location=proto.location,
                            code_suffix="ISP_ROLE_INTERFACE",
                        ),
                        self.evidence(
                            description=f"Implemented by {len(rec_impls)} targeted classes without bloated contract obligations",
                            weight=0.30,
                            location=proto.location,
                            code_suffix="ISP_CLEAN_IMPLEMENTATION",
                        ),
                    ]

                    detection = self.create_detection(
                        target_name=proto.name,
                        target_kind="segregated_role_interface",
                        evidences=evidences,
                        primary_location=proto.location,
                        related_locations=[r.location for r in rec_impls],
                        summary=f"ISP Adherence: Role interface '{proto.name}' is segregated and focused ({method_count} methods)",
                        base_score=0.30,
                    )
                    detection.pattern_category = PatternCategory.PRINCIPLE
                    detections.append(detection)

        return detections
