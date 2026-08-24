"""Mediator Pattern Detection Rule."""

from __future__ import annotations

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import PatternType, SourceLocation


class MediatorPatternRule(BasePatternRule):
    """Detects Mediator / Event Broker Hub pattern instances in Clojure.

    Indicators:
    - Records or state containers named `EventBus`, `MessageHub`, `Mediator`, `Dispatcher`, `EventBroker`.
    - Protocols defining `publish`, `subscribe`, `dispatch`, `broadcast` methods to decouple sender/receiver.
    - Centralized routing of cross-component messages without direct mutual references.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.MEDIATOR

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []

        # 1. Mediator Protocols (e.g. EventBus, MessageBroker)
        for proto in model.all_protocols():
            if proto.name.endswith("Rule") or proto.name.endswith("Test"):
                continue
            name_lower = proto.name.lower()
            methods_lower = [m.name.split(".")[-1].lower() for m in proto.methods]
            is_mediator_proto = any(k in name_lower for k in ("mediator", "eventbus", "messagebroker", "dispatcherhub"))
            has_pubsub_methods = any(m in ("publish", "subscribe", "broadcast", "dispatch", "emit", "send_message", "notify_colleagues") for m in methods_lower)

            if (is_mediator_proto and has_pubsub_methods) or (len(methods_lower) >= 2 and has_pubsub_methods):
                evidences = [
                    self.evidence(
                        description=f"Protocol '{proto.name}' defines central mediator message coordination methods: {', '.join(m.name for m in proto.methods)}",
                        weight=0.60,
                        location=proto.location,
                        code_suffix="MEDIATOR_PROTOCOL",
                    ),
                ]
                rec_impls = model.find_records_implementing(proto.name)
                related_locs: list[SourceLocation] = []
                if rec_impls:
                    evidences.append(
                        self.evidence(
                            description=f"Implemented by concrete mediator hub record(s): {', '.join(r.name for r in rec_impls)}",
                            weight=0.35,
                            location=rec_impls[0].location,
                            code_suffix="MEDIATOR_RECORD_IMPL",
                        )
                    )
                    related_locs.extend(r.location for r in rec_impls)

                detections.append(
                    self.create_detection(
                        target_name=proto.name,
                        target_kind="mediator_protocol",
                        evidences=evidences,
                        primary_location=proto.location,
                        related_locations=related_locs,
                        summary=f"Mediator pattern: protocol '{proto.name}' acts as central event/message broker decoupling components",
                        base_score=0.30,
                    )
                )

        # 2. Mediator Records (e.g. EventBus record holding subscriber registry)
        for rec in model.all_records():
            if rec.name.endswith("Rule") or rec.name.endswith("Test"):
                continue
            name_lower = rec.name.lower()
            has_colleagues = any(
                any(k in f.lower() for k in ("subscriber", "listener", "handler", "colleague", "sub", "registry"))
                for f in rec.fields
            )
            if any(k in name_lower for k in ("eventbus", "messagehub", "mediator", "eventbroker")) and has_colleagues:
                evidences = [
                    self.evidence(
                        description=f"Record '{rec.name}' encapsulates centralized mediator broker state and subscriber registry",
                        weight=0.65,
                        location=rec.location,
                        code_suffix="MEDIATOR_RECORD",
                    ),
                ]
                detections.append(
                    self.create_detection(
                        target_name=rec.name,
                        target_kind="mediator_hub_record",
                        evidences=evidences,
                        primary_location=rec.location,
                        related_locations=[],
                        summary=f"Mediator pattern: record '{rec.name}' mediates communication between decoupled subsystems",
                        base_score=0.30,
                    )
                )

        return detections
