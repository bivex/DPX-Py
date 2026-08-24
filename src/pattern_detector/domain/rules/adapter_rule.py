"""Adapter / Protocol Extension Pattern Detection Rule."""

from __future__ import annotations

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

        # 1. Extensions via extend-type or extend-protocol
        for ext in model.all_extensions():
            evidences: list[Evidence] = []
            related_locs: list[SourceLocation] = []

            evidences.append(
                self.evidence(
                    description=f"Non-intrusive extension adapting type '{ext.target_type}' to protocol '{ext.protocol_name}'",
                    weight=0.65,
                    location=ext.location,
                    code_suffix="EXTERNAL_PROTOCOL_EXTENSION",
                )
            )

            # Check if target_type is standard or external (Java class or core type)
            is_core_or_java = (
                ext.target_type.startswith("java.")
                or ext.target_type.startswith("String")
                or ext.target_type.startswith("Number")
                or ext.target_type.startswith("nil")
                or ext.target_type.startswith("Object")
                or ext.target_type.startswith("clojure.")
                or "." in ext.target_type
            )
            if is_core_or_java:
                evidences.append(
                    self.evidence(
                        description=f"Adapts external/standard host platform type '{ext.target_type}' without modifying source class",
                        weight=0.30,
                        location=ext.location,
                        code_suffix="EXTERNAL_TYPE_ADAPTATION",
                    )
                )

            # Check matching protocol
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

            detections.append(
                self.create_detection(
                    target_name=f"{ext.target_type}->{ext.protocol_name}",
                    target_kind="protocol_adapter",
                    evidences=evidences,
                    primary_location=ext.location,
                    related_locations=related_locs,
                    summary=f"Adapter pattern: adapts type '{ext.target_type}' to protocol '{ext.protocol_name}'",
                    base_score=0.15,
                )
            )

        # 2. C++ OOP Adapter Pattern (Object & Class Adapters)
        for rec in model.all_records():
            name_lower = rec.name.lower()
            is_adapter_named = "adapter" in name_lower or "wrapper" in name_lower

            # Check if implements a target protocol
            implemented_protocols = [
                proto.name for proto in model.all_protocols()
                if rec.implements_protocol(proto.name) or any(r.name == rec.name for r in model.find_records_implementing(proto.name))
            ]

            # Check for wrapped adaptee field
            adaptee_fields = [
                f for f in rec.fields
                if any(k in f.lower() for k in ("adaptee", "delegate", "target", "source", "wrapped", "impl", "client"))
            ]

            # Exclude non-adapter GoF roles when class is not explicitly named Adapter
            if not is_adapter_named and any(
                k in name_lower for k in ("abstraction", "bridge", "proxy", "decorator", "flyweight", "observer", "subject", "mediator", "state", "command", "strategy", "visitor")
            ):
                continue

            if (is_adapter_named and (implemented_protocols or adaptee_fields)) or (implemented_protocols and adaptee_fields):
                evidences = []
                related_locs = []

                if is_adapter_named:
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
                            description=f"Implements target client interface(s): {', '.join(implemented_protocols)}",
                            weight=0.40,
                            location=rec.location,
                            code_suffix="ADAPTER_IMPLEMENTS_TARGET",
                        )
                    )
                    for p_name in implemented_protocols:
                        p = model.find_protocol(p_name)
                        if p:
                            related_locs.append(p.location)

                if adaptee_fields:
                    evidences.append(
                        self.evidence(
                            description=f"Maintains wrapped adaptee delegate field(s): {', '.join(adaptee_fields)}",
                            weight=0.40,
                            location=rec.location,
                            code_suffix="ADAPTER_ADAPTEE_FIELD",
                        )
                    )

                detections.append(
                    self.create_detection(
                        target_name=rec.name,
                        target_kind="cpp_adapter_class",
                        evidences=evidences,
                        primary_location=rec.location,
                        related_locations=related_locs,
                        summary=f"Adapter pattern: class '{rec.name}' adapts legacy/incompatible interface to client protocol",
                        base_score=0.30,
                    )
                )

        return detections
