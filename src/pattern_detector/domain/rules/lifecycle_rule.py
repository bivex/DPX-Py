"""Lifecycle Component Pattern Detection Rule."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternType


class LifecycleComponentPatternRule(BasePatternRule):
    """Detects Lifecycle Component Pattern (Stuart Sierra Component / Integrant / Mount).

    Indicators:
    - Protocols or records implementing `Lifecycle` with `start` and `stop` lifecycle transitions.
    - Records implementing `start` and `stop` methods.
    - Component dependency maps or system builders.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.LIFECYCLE_COMPONENT

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        detections.extend(self._detect_lifecycle_protocols(model))
        detections.extend(self._detect_lifecycle_records(model))
        return detections

    def _detect_lifecycle_protocols(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for proto in model.all_protocols():
            method_names = {m.name for m in proto.methods}
            if {"start", "stop"}.issubset(method_names) or "lifecycle" in proto.name.lower():
                matched_methods = [m for m in ("start", "stop") if proto.has_method(m)]
                proto_evidences = [
                    self.evidence(
                        description=f"Protocol '{proto.name}' defines explicit component lifecycle transitions ({', '.join(matched_methods)})",
                        weight=0.60,
                        location=proto.location,
                        code_suffix="LIFECYCLE_PROTOCOL",
                    )
                ]
                results.append(
                    self.create_detection(
                        target_name=proto.name,
                        target_kind="lifecycle_protocol",
                        evidences=proto_evidences,
                        primary_location=proto.location,
                        summary=f"Lifecycle pattern: protocol '{proto.name}' defines system lifecycle contract",
                        base_score=0.20,
                    )
                )
        return results

    def _detect_lifecycle_records(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for rec in model.all_records():
            det = self._analyze_lifecycle_record(rec)
            if det:
                results.append(det)
        return results

    def _analyze_lifecycle_record(self, rec: Any) -> Detection | None:
        implements_lifecycle = any("lifecycle" in p.lower() for p in rec.implemented_protocols)
        has_start = any(m.name.split(".")[-1] == "start" for m in rec.methods)
        has_stop = any(m.name.split(".")[-1] == "stop" for m in rec.methods)

        if not (implements_lifecycle or (has_start and has_stop)):
            return None

        evidences = self._build_record_lifecycle_evidences(rec, implements_lifecycle, has_start, has_stop)
        return self.create_detection(
            target_name=rec.name,
            target_kind="lifecycle_component",
            evidences=evidences,
            primary_location=rec.location,
            related_locations=[],
            summary=f"Lifecycle Component pattern: stateful component '{rec.name}' with start/stop lifecycle",
            base_score=0.15,
        )

    def _build_record_lifecycle_evidences(
        self, rec: Any, implements_lifecycle: bool, has_start: bool, has_stop: bool
    ) -> list[Evidence]:
        evidences: list[Evidence] = []
        if implements_lifecycle:
            evidences.append(
                self.evidence(
                    description=f"Record '{rec.name}' explicitly implements Lifecycle protocol",
                    weight=0.55,
                    location=rec.location,
                    code_suffix="IMPLEMENTS_LIFECYCLE",
                )
            )
        if has_start:
            evidences.append(
                self.evidence(
                    description=f"Record '{rec.name}' implements 'start' lifecycle method",
                    weight=0.35,
                    location=rec.location,
                    code_suffix="HAS_START_METHOD",
                )
            )
        if has_stop:
            evidences.append(
                self.evidence(
                    description=f"Record '{rec.name}' implements 'stop' lifecycle method",
                    weight=0.35,
                    location=rec.location,
                    code_suffix="HAS_STOP_METHOD",
                )
            )
        return evidences
