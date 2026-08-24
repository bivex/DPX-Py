"""Adapter / Protocol Extension Pattern Detection Rule."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternType, SourceLocation


class AdapterPatternRule(BasePatternRule):
    """Detects Adapter Pattern instances in Clojure.

    Indicators:
    - `extend-type` or `extend-protocol` adapting existing external types/classes to Clojure protocols.
    - Adapter wrapper records encapsulating an existing object and implementing a target protocol.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.ADAPTER

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        detections.extend(self._detect_extension_adapters(model))
        detections.extend(self._detect_oop_adapters(model))
        return detections

    def _detect_extension_adapters(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for ext in model.all_extensions():
            det = self._analyze_extension_adapter(ext, model)
            results.append(det)
        return results

    def _analyze_extension_adapter(self, ext: Any, model: CodeModel) -> Detection:
        evidences = [
            self.evidence(
                description=f"Non-intrusive extension adapting type '{ext.target_type}' to protocol '{ext.protocol_name}'",
                weight=0.65,
                location=ext.location,
                code_suffix="EXTERNAL_PROTOCOL_EXTENSION",
            )
        ]
        related_locs: list[SourceLocation] = []

        if self._is_core_or_java_type(ext.target_type):
            evidences.append(
                self.evidence(
                    description=f"Adapts external/standard host platform type '{ext.target_type}' without modifying source class",
                    weight=0.30,
                    location=ext.location,
                    code_suffix="EXTERNAL_TYPE_ADAPTATION",
                )
            )

        proto = model.find_protocol(ext.protocol_name)
        if proto:
            evidences.append(
                self.evidence(
                    description=f"Provides protocol method implementations: {', '.join(m.name for m in ext.methods)}",
                    weight=0.20,
                    location=proto.location,
                    code_suffix="ADAPTER_METHODS_IMPLEMENTED",
                )
            )
            related_locs.append(proto.location)

        return self.create_detection(
            target_name=f"{ext.target_type}->{ext.protocol_name}",
            target_kind="protocol_adapter",
            evidences=evidences,
            primary_location=ext.location,
            related_locations=related_locs,
            summary=f"Adapter pattern: adapts type '{ext.target_type}' to protocol '{ext.protocol_name}'",
            base_score=0.15,
        )

    def _is_core_or_java_type(self, target_type: str) -> bool:
        prefixes = ("java.", "String", "Number", "nil", "Object", "clojure.")
        return target_type.startswith(prefixes) or "." in target_type

    def _detect_oop_adapters(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for rec in model.all_records():
            if not rec.name.endswith(("Rule", "Test")):
                det = self._analyze_adapter_record(rec, model)
                if det:
                    results.append(det)
        return results

    def _analyze_adapter_record(self, rec: Any, model: CodeModel) -> Detection | None:
        name_lower = rec.name.lower()
        is_adapter_named = "adapter" in name_lower or "wrapper" in name_lower
        implemented_protocols = self._find_implemented_protocols(rec, model)
        adaptee_fields = self._find_adaptee_fields(rec.fields)

        if not (is_adapter_named or (implemented_protocols and adaptee_fields)):
            return None

        evidences = self._build_oop_adapter_evidences(rec, is_adapter_named, implemented_protocols, adaptee_fields)
        return self.create_detection(
            target_name=rec.name,
            target_kind="adapter_class",
            evidences=evidences,
            primary_location=rec.location,
            related_locations=[],
            summary=f"Adapter pattern: class '{rec.name}' adapts adaptee to target interface",
            base_score=0.25,
        )

    def _find_implemented_protocols(self, rec: Any, model: CodeModel) -> list[str]:
        results = []
        for proto in model.all_protocols():
            if rec.implements_protocol(proto.name) or any(
                r.name == rec.name for r in model.find_records_implementing(proto.name)
            ):
                results.append(proto.name)
        return results

    def _find_adaptee_fields(self, fields: list[str]) -> list[str]:
        keywords = ("adaptee", "delegate", "target", "source", "wrapped", "impl", "client")
        results = []
        for f in fields:
            if any(k in f.lower() for k in keywords):
                results.append(f)
        return results

    def _build_oop_adapter_evidences(
        self, rec: Any, is_named: bool, implemented_protocols: list[str], adaptee_fields: list[str]
    ) -> list[Evidence]:
        evidences = []
        if is_named:
            evidences.append(
                self.evidence(
                    description=f"Class '{rec.name}' follows Adapter pattern naming convention",
                    weight=0.45,
                    location=rec.location,
                    code_suffix="ADAPTER_NAMING",
                )
            )
        if implemented_protocols:
            evidences.append(
                self.evidence(
                    description=f"Implements target interface protocol(s): {', '.join(implemented_protocols)}",
                    weight=0.40,
                    location=rec.location,
                    code_suffix="ADAPTER_IMPLEMENTS_TARGET",
                )
            )
        if adaptee_fields:
            evidences.append(
                self.evidence(
                    description=f"Maintains reference to adapted instance (adaptee): {', '.join(adaptee_fields)}",
                    weight=0.35,
                    location=rec.location,
                    code_suffix="ADAPTEE_FIELD",
                )
            )
        return evidences
