"""Prototype Pattern Detection Rule."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternType


class PrototypePatternRule(BasePatternRule):
    """Detects Prototype / Cloneable Variant pattern instances in Clojure.

    Indicators:
    - Protocols defining `clone`, `copy-with`, `prototype`, `derive-from`.
    - Functions named `clone-*`, `derive-*`, `copy-with-*` copying a prototype instance with override maps.
    - Records implementing prototype/cloning protocols.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.PROTOTYPE

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        detections.extend(self._detect_prototype_protocols(model))
        detections.extend(self._detect_prototype_functions(model))
        return detections

    def _detect_prototype_protocols(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for proto in model.all_protocols():
            det = self._analyze_proto_protocol(proto, model)
            if det:
                results.append(det)
        return results

    def _analyze_proto_protocol(self, proto: Any, model: CodeModel) -> Detection | None:
        if not self._is_prototype_proto(proto):
            return None

        rec_impls = model.find_records_implementing(proto.name)
        evidences = self._build_proto_evidences(proto, rec_impls)
        related_locs = [r.location for r in rec_impls]

        return self.create_detection(
            target_name=proto.name,
            target_kind="prototype_protocol",
            evidences=evidences,
            primary_location=proto.location,
            related_locations=related_locs,
            summary=f"Prototype pattern: protocol '{proto.name}' defines instance cloning and derivation interface",
            base_score=0.30,
        )

    def _is_prototype_proto(self, proto: Any) -> bool:
        name_lower = proto.name.lower()
        if any(k in name_lower for k in ("prototype", "cloneable", "copiable", "derive")):
            return True
        clone_names = ("clone", "copy-with", "derive", "duplicate")
        for m in proto.methods:
            if m.name.lower() in clone_names:
                return True
        return False

    def _build_proto_evidences(self, proto: Any, rec_impls: list[Any]) -> list[Evidence]:
        evidences = [
            self.evidence(
                description=f"Protocol '{proto.name}' defines prototype cloning methods: {', '.join(m.name for m in proto.methods)}",
                weight=0.55,
                location=proto.location,
                code_suffix="PROTOTYPE_PROTOCOL",
            ),
        ]
        if rec_impls:
            evidences.append(
                self.evidence(
                    description=f"Implemented by {len(rec_impls)} prototype records: {', '.join(r.name for r in rec_impls)}",
                    weight=0.35,
                    location=rec_impls[0].location,
                    code_suffix="CONCRETE_PROTOTYPES",
                )
            )
        return evidences

    def _detect_prototype_functions(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for fn in model.all_functions():
            if not fn.is_multimethod and not fn.parent_multimethod:
                det = self._analyze_proto_function(fn)
                if det:
                    results.append(det)
        return results

    def _analyze_proto_function(self, fn: Any) -> Detection | None:
        name_lower = fn.name.lower()
        if not name_lower.startswith(("clone-", "derive-", "copy-with-", "duplicate-")):
            return None

        params = [p.lower() for plist in fn.parameter_lists for p in plist]
        has_proto_param = any(
            "proto" in p or "orig" in p or "base" in p or "template" in p or "inst" in p for p in params
        )
        has_merge = any(k in fn.body_text for k in ("merge", "assoc", "update", "into"))

        if not (has_proto_param or has_merge):
            return None

        evidences = [
            self.evidence(
                description=f"Function '{fn.name}' copies prototype instance applying override parameters",
                weight=0.60,
                location=fn.location,
                code_suffix="PROTOTYPE_DERIVE_FN",
            ),
        ]
        return self.create_detection(
            target_name=fn.name,
            target_kind="prototype_clone_fn",
            evidences=evidences,
            primary_location=fn.location,
            related_locations=[],
            summary=f"Prototype pattern: '{fn.name}' creates modified variants from prototype templates",
            base_score=0.25,
        )
