"""Proxy Pattern Detection Rule."""

from __future__ import annotations

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import PatternType


class ProxyPatternRule(BasePatternRule):
    """Detects Proxy / Lazy Virtual Proxy pattern instances in Clojure.

    Indicators:
    - Native `proxy` macro invocations creating Java interop or surrogate instances.
    - Lazy virtual proxy wrappers using `delay` to defer expensive object creation until first deref.
    - Functions/records acting as intermediaries delegating calls to an underlying target.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.PROXY

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []

        # 1. Inspect State models for lazy delays / promises (Virtual Proxy)
        for state in model.all_states():
            if state.kind == "delay":
                evidences = [
                    self.evidence(
                        description=f"State '{state.name}' creates a lazy virtual proxy using 'delay', deferring instantiation until accessed",
                        weight=0.65,
                        location=state.location,
                        code_suffix="LAZY_DELAY_PROXY",
                    ),
                ]
                if state.is_once:
                    evidences.append(
                        self.evidence(
                            description="Combines 'defonce' with lazy delay ensuring thread-safe memoized proxy initialization",
                            weight=0.30,
                            location=state.location,
                            code_suffix="DEFONCE_LAZY_PROXY",
                        )
                    )
                detections.append(
                    self.create_detection(
                        target_name=state.name,
                        target_kind="virtual_proxy_state",
                        evidences=evidences,
                        primary_location=state.location,
                        related_locations=[],
                        summary=f"Virtual Proxy: lazy delay '{state.name}' controls deferred access and instantiation of resource",
                        base_score=0.25,
                    )
                )

        # 2. Inspect Functions using native `proxy`
        for fn in model.all_functions():
            if "proxy" in fn.calls or "(proxy " in fn.body_text or "(proxy[" in fn.body_text:
                evidences = [
                    self.evidence(
                        description=f"Function '{fn.name}' instantiates a dynamic host proxy surrogate using (proxy ...)",
                        weight=0.70,
                        location=fn.location,
                        code_suffix="NATIVE_PROXY_MACRO",
                    ),
                ]
                if fn.returns_closure:
                    evidences.append(
                        self.evidence(
                            description="Returns proxy surrogate instance encapsulated within closure",
                            weight=0.25,
                            location=fn.location,
                            code_suffix="RETURNS_PROXY_CLOSURE",
                        )
                    )
                detections.append(
                    self.create_detection(
                        target_name=fn.name,
                        target_kind="proxy_factory_fn",
                        evidences=evidences,
                        primary_location=fn.location,
                        related_locations=[],
                        summary=f"Proxy pattern: '{fn.name}' generates surrogate proxy object wrapping target behavior",
                        base_score=0.25,
                    )
                )

        # 3. OOP Proxy Pattern in C++
        for rec in model.all_records():
            name_lower = rec.name.lower()
            if "proxy" in name_lower:
                evidences = [
                    self.evidence(
                        description=f"Class '{rec.name}' follows Proxy surrogate naming convention",
                        weight=0.50,
                        location=rec.location,
                        code_suffix="PROXY_CLASS_NAMING",
                    )
                ]
                has_subject_field = any(
                    k in f.lower() for f in rec.fields for k in ("subject", "real", "target", "service", "impl")
                )
                if has_subject_field:
                    evidences.append(
                        self.evidence(
                            description=f"Class '{rec.name}' maintains reference to wrapped real subject: {', '.join([f for f in rec.fields if any(k in f.lower() for k in ('subject', 'real', 'target', 'service', 'impl'))])}",
                            weight=0.40,
                            location=rec.location,
                            code_suffix="PROXY_TARGET_FIELD",
                        )
                    )
                if rec.implemented_protocols:
                    evidences.append(
                        self.evidence(
                            description=f"Implements subject interface '{', '.join(rec.implemented_protocols)}' to act as polymorphic surrogate",
                            weight=0.35,
                            location=rec.location,
                            code_suffix="PROXY_IMPLEMENTS_SUBJECT",
                        )
                    )
                detections.append(
                    self.create_detection(
                        target_name=rec.name,
                        target_kind="proxy_class",
                        evidences=evidences,
                        primary_location=rec.location,
                        summary=f"Proxy pattern: class '{rec.name}' acts as surrogate controlling access to real subject",
                        base_score=0.30,
                    )
                )

        return detections
