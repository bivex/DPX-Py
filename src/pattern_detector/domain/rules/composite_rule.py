"""Composite Pattern Detection Rule."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternType


class CompositePatternRule(BasePatternRule):
    """Detects Composite / Tree Structure pattern instances in Clojure.

    Indicators:
    - Protocols defining component interfaces (e.g. `Component`, `Node`, `Element`, `Shape`, `View`).
    - Records implementing the protocol where at least one represents a Composite/Container (holds children)
      and one represents a Leaf element.
    - Uniform treatment of leaf and composite instances.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.COMPOSITE

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        for proto in model.all_protocols():
            det = self._analyze_composite_proto(proto, model)
            if det:
                detections.append(det)
        return detections

    def _analyze_composite_proto(self, proto: Any, model: CodeModel) -> Detection | None:
        rec_impls = model.find_records_implementing(proto.name)
        if len(rec_impls) < 2:
            return None

        composite_recs, leaf_recs = self._classify_composite_records(rec_impls, proto.name)
        if not (composite_recs and leaf_recs):
            return None

        evidences = self._build_composite_evidences(proto, composite_recs, leaf_recs)
        related_locs = [r.location for r in rec_impls]

        return self.create_detection(
            target_name=proto.name,
            target_kind="composite_hierarchy",
            evidences=evidences,
            primary_location=proto.location,
            related_locations=related_locs,
            summary=f"Composite pattern: protocol '{proto.name}' unifies leaf and composite container records in part-whole hierarchy",
            base_score=0.30,
        )

    def _classify_composite_records(self, rec_impls: list[Any], proto_name: str) -> tuple[list[Any], list[Any]]:
        composite_recs = []
        leaf_recs = []
        for rec in rec_impls:
            if self._is_composite_record(rec):
                composite_recs.append(rec)
            else:
                leaf_recs.append(rec)

        if not composite_recs and "composite" in proto_name.lower() and len(rec_impls) >= 2:
            leaf_recs = [rec_impls[0]]
            composite_recs = list(rec_impls[1:])

        return composite_recs, leaf_recs

    def _is_composite_record(self, rec: Any) -> bool:
        fields_lower = [f.lower() for f in rec.fields]
        is_composite_field = any(
            k in f
            for f in fields_lower
            for k in ("children", "items", "components", "elements", "nodes", "members", "subs")
        )
        return is_composite_field or any(
            k in rec.name.lower()
            for k in ("composite", "group", "container", "panel", "tree", "compound", "sentence", "word")
        )

    def _build_composite_evidences(self, proto: Any, composite_recs: list[Any], leaf_recs: list[Any]) -> list[Evidence]:
        return [
            self.evidence(
                description=f"Protocol '{proto.name}' defines uniform component interface for both leaves and containers",
                weight=0.50,
                location=proto.location,
                code_suffix="COMPOSITE_PROTOCOL",
            ),
            self.evidence(
                description=f"Identified composite container record(s) holding child hierarchies: {', '.join(r.name for r in composite_recs)}",
                weight=0.45,
                location=composite_recs[0].location,
                code_suffix="COMPOSITE_CONTAINER_RECORDS",
            ),
            self.evidence(
                description=f"Identified leaf element record(s): {', '.join(r.name for r in leaf_recs)}",
                weight=0.35,
                location=leaf_recs[0].location,
                code_suffix="LEAF_ELEMENT_RECORDS",
            ),
        ]
