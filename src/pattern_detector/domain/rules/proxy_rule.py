"""Proxy Pattern Detection Rule."""

from __future__ import annotations

from typing import Any

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
        detections.extend(self._detect_lazy_delay_proxies(model))
        detections.extend(self._detect_oop_proxies(model))
        return detections

    def _detect_lazy_delay_proxies(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
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
                results.append(
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
        return results

    def _detect_oop_proxies(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for rec in model.all_records():
            if not rec.name.endswith(("Rule", "Test")):
                det = self._analyze_proxy_record(rec)
                if det:
                    results.append(det)
        return results

    def _analyze_proxy_record(self, rec: Any) -> Detection | None:
        if "proxy" not in rec.name.lower() or not rec.implemented_protocols:
            return None

        has_subject_field = any(
            k in f.lower() for f in rec.fields for k in ("subject", "_subject", "real", "_real", "target", "_target")
        )
        if not has_subject_field:
            return None

        evidences = [
            self.evidence(
                description=f"Class '{rec.name}' follows Proxy surrogate naming convention",
                weight=0.50,
                location=rec.location,
                code_suffix="PROXY_CLASS_NAMING",
            ),
            self.evidence(
                description=f"Class '{rec.name}' maintains reference to wrapped real subject: {', '.join([f for f in rec.fields if any(k in f.lower() for k in ('subject', 'real', 'target'))])}",
                weight=0.40,
                location=rec.location,
                code_suffix="PROXY_TARGET_FIELD",
            ),
            self.evidence(
                description=f"Implements subject interface '{', '.join(rec.implemented_protocols)}' to act as polymorphic surrogate",
                weight=0.35,
                location=rec.location,
                code_suffix="PROXY_IMPLEMENTS_SUBJECT",
            ),
        ]
        return self.create_detection(
            target_name=rec.name,
            target_kind="proxy_class",
            evidences=evidences,
            primary_location=rec.location,
            summary=f"Proxy pattern: class '{rec.name}' acts as surrogate controlling access to real subject",
            base_score=0.30,
        )
