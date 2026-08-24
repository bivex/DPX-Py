"""Abstract Factory Pattern Detection Rule."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternType


class AbstractFactoryRule(BasePatternRule):
    """Detects Abstract Factory pattern instances in Clojure.

    Indicators:
    - Protocols defining multiple related factory creation methods (e.g. create-*, make-*, build-*).
    - Records implementing abstract factory protocols to produce families of related components.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.ABSTRACT_FACTORY

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        for proto in model.all_protocols():
            det = self._analyze_factory_protocol(proto, model)
            if det:
                detections.append(det)
        return detections

    def _analyze_factory_protocol(self, proto: Any, model: CodeModel) -> Detection | None:
        name_lower = proto.name.lower()
        if "builder" in name_lower or name_lower == "creator":
            return None

        is_factory_proto = "factory" in name_lower
        factory_methods = [
            m for m in proto.methods if m.name.lower().startswith(("create-", "make-", "new-", "create", "make", "new"))
        ]

        if len(factory_methods) < 2 and not (len(factory_methods) >= 1 and is_factory_proto):
            return None

        implementing_records = model.find_records_implementing(proto.name)
        evidences = self._build_factory_evidences(proto, factory_methods, is_factory_proto, implementing_records)
        related_locs = [r.location for r in implementing_records]

        return self.create_detection(
            target_name=proto.name,
            target_kind="abstract_factory_protocol",
            evidences=evidences,
            primary_location=proto.location,
            related_locations=related_locs,
            summary=f"Abstract Factory: protocol '{proto.name}' declares family of object creation interfaces",
            base_score=0.30,
        )

    def _build_factory_evidences(
        self, proto: Any, factory_methods: list[Any], is_factory_proto: bool, implementing_records: list[Any]
    ) -> list[Evidence]:
        evidences: list[Evidence] = [
            self.evidence(
                description=f"Protocol '{proto.name}' defines family of {len(factory_methods)} creation methods: {', '.join(m.name for m in factory_methods)}",
                weight=min(0.60, 0.35 + 0.10 * len(factory_methods)),
                location=proto.location,
                code_suffix="FACTORY_PROTOCOL_METHODS",
            )
        ]
        if is_factory_proto:
            evidences.append(
                self.evidence(
                    description=f"Protocol '{proto.name}' follows Abstract Factory naming convention",
                    weight=0.35,
                    location=proto.location,
                    code_suffix="FACTORY_PROTOCOL_NAMING",
                )
            )
        if implementing_records:
            evidences.append(
                self.evidence(
                    description=f"Implemented by {len(implementing_records)} concrete factory record(s): {', '.join(r.name for r in implementing_records)}",
                    weight=min(0.40, 0.20 + 0.10 * len(implementing_records)),
                    location=implementing_records[0].location,
                    code_suffix="CONCRETE_FACTORY_RECORDS",
                )
            )
        return evidences
