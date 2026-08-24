"""Bridge Pattern Detection Rule."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import PatternType


class BridgePatternRule(BasePatternRule):
    """Detects Bridge / Decoupled Abstraction & Implementation pattern instances.

    Indicators:
    - High-level abstraction protocol or record holding an injected implementation driver/engine field.
    - Low-level implementation protocol (e.g. `*Driver`, `*Backend`, `*Engine`, `*Platform`).
    - Delegation from abstraction methods to implementation driver methods.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.BRIDGE

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        driver_protos = self._find_driver_protocols(model)

        for driver_p in driver_protos:
            detections.extend(self._find_bridge_records(driver_p, model))

        return detections

    def _find_driver_protocols(self, model: CodeModel) -> list[Any]:
        keywords = ("implementor", "driver", "backend", "renderingengine", "platformapi")
        results = []
        for p in model.all_protocols():
            if any(k in p.name.lower() for k in keywords):
                results.append(p)
        return results

    def _find_bridge_records(self, driver_p: Any, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for rec in model.all_records():
            if not rec.name.endswith(("Rule", "Test")) and not rec.implements_protocol(driver_p.name):
                matching_fields = self._check_matching_driver_fields(rec, driver_p)
                if matching_fields:
                    results.append(self._create_bridge_detection(rec, driver_p, matching_fields))
        return results

    def _check_matching_driver_fields(self, rec: Any, driver_p: Any) -> list[str]:
        p_name = driver_p.name.lower()
        valid_field_names = (
            "driver",
            "_driver",
            "implementor",
            "_implementor",
            "backend",
            "_backend",
            p_name,
            f"_{p_name}",
        )
        results = []
        for f in rec.fields:
            if f.lower() in valid_field_names:
                results.append(f)
        return results

    def _create_bridge_detection(self, rec: Any, driver_p: Any, matching_fields: list[str]) -> Detection:
        evidences = [
            self.evidence(
                description=f"Record '{rec.name}' maintains decoupled bridge reference to implementation driver field: {', '.join(matching_fields)}",
                weight=0.55,
                location=rec.location,
                code_suffix="BRIDGE_ABSTRACTION_RECORD",
            ),
            self.evidence(
                description=f"Driver implementation protocol '{driver_p.name}' defines concrete backend interface",
                weight=0.40,
                location=driver_p.location,
                code_suffix="BRIDGE_DRIVER_PROTOCOL",
            ),
        ]
        return self.create_detection(
            target_name=rec.name,
            target_kind="bridge_abstraction",
            evidences=evidences,
            primary_location=rec.location,
            related_locations=[driver_p.location],
            summary=f"Bridge pattern: abstraction record '{rec.name}' decouples domain logic from '{driver_p.name}' backend implementation",
            base_score=0.30,
        )
