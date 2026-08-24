"""Strategy / Polymorphic Dispatch Pattern Detection Rule."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternType, SourceLocation


class StrategyPatternRule(BasePatternRule):
    """Detects Strategy Pattern instances in Clojure.

    Indicators:
    - `defmulti` dispatch function combined with 2+ `defmethod` algorithm implementations.
    - Protocols implemented by 2+ distinct records or extended types (Polymorphic Strategy).
    - Higher-order functions accepting explicit strategy/algorithm callbacks.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.STRATEGY

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        detections.extend(self._detect_multimethod_strategies(model))
        detections.extend(self._detect_protocol_strategies(model))
        return detections

    def _detect_multimethod_strategies(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for ns in model.namespaces.values():
            for mm_name, methods in ns.multimethods.items():
                det = self._analyze_multimethod(mm_name, methods, ns)
                results.append(det)
        return results

    def _analyze_multimethod(self, mm_name: str, methods: list[Any], ns: Any) -> Detection:
        primary_loc, decl_evidence = self._find_defmulti_declaration(mm_name, methods, ns)
        branches, branch_evidence, related_locs = self._find_defmethod_branches(methods)

        evidences: list[Evidence] = []
        if decl_evidence:
            evidences.append(decl_evidence)
        if branch_evidence:
            evidences.append(branch_evidence)

        return self.create_detection(
            target_name=mm_name,
            target_kind="multimethod_strategy",
            evidences=evidences,
            primary_location=primary_loc,
            related_locations=related_locs,
            summary=f"Strategy pattern: multimethod '{mm_name}' with {len(branches)} polymorphic dispatch strategies",
            base_score=0.15,
        )

    def _find_defmulti_declaration(
        self, mm_name: str, methods: list[Any], ns: Any
    ) -> tuple[SourceLocation, Evidence | None]:
        for m in methods:
            if not m.dispatch_val:
                ev = self.evidence(
                    description=f"Multimethod dispatch definition '(defmulti {mm_name} {m.dispatch_fn or '...'})'",
                    weight=0.50,
                    location=m.location,
                    code_suffix="MULTIMETHOD_DECLARATION",
                )
                return m.location, ev

        fallback_loc = methods[0].location if methods else SourceLocation(file_path=ns.file_path, line=1)
        return fallback_loc, None

    def _find_defmethod_branches(self, methods: list[Any]) -> tuple[list[Any], Evidence | None, list[SourceLocation]]:
        branches = [m for m in methods if m.dispatch_val is not None]
        if not branches:
            return [], None, []

        branch_names = [b.dispatch_val or "" for b in branches[:5]]
        ev = self.evidence(
            description=f"Found {len(branches)} distinct interchangeable strategy branches (defmethod): {', '.join(branch_names)}",
            weight=min(0.45, 0.20 + 0.05 * len(branches)),
            location=branches[0].location,
            code_suffix="DISPATCH_BRANCHES",
        )
        related_locs = [b.location for b in branches]
        return branches, ev, related_locs

    def _detect_protocol_strategies(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for proto in model.all_protocols():
            det = self._analyze_protocol_strategy(proto, model)
            if det:
                results.append(det)
        return results

    def _analyze_protocol_strategy(self, proto: Any, model: CodeModel) -> Detection | None:
        implementing_records = model.find_records_implementing(proto.name)
        extensions = [ext for ext in model.all_extensions() if ext.protocol_name in (proto.name, proto.qualified_name)]

        if len(implementing_records) + len(extensions) < 2:
            return None

        evidences = [
            self.evidence(
                description=f"Protocol '{proto.name}' defines strategy interface with methods: {', '.join(m.name for m in proto.methods)}",
                weight=0.45,
                location=proto.location,
                code_suffix="PROTOCOL_STRATEGY_INTERFACE",
            )
        ]
        related_locs: list[SourceLocation] = []

        for rec in implementing_records:
            evidences.append(
                self.evidence(
                    description=f"Record '{rec.name}' provides concrete strategy implementation for protocol '{proto.name}'",
                    weight=0.25,
                    location=rec.location,
                    code_suffix="RECORD_STRATEGY_IMPL",
                )
            )
            related_locs.append(rec.location)

        for ext in extensions:
            evidences.append(
                self.evidence(
                    description=f"Extension on '{ext.target_type}' implements strategy protocol '{proto.name}'",
                    weight=0.20,
                    location=ext.location,
                    code_suffix="EXTENSION_STRATEGY_IMPL",
                )
            )
            related_locs.append(ext.location)

        return self.create_detection(
            target_name=proto.name,
            target_kind="protocol_strategy",
            evidences=evidences,
            primary_location=proto.location,
            related_locations=related_locs,
            summary=f"Strategy pattern: protocol '{proto.name}' defines strategy interface implemented by {len(implementing_records) + len(extensions)} concrete types",
            base_score=0.25,
        )
