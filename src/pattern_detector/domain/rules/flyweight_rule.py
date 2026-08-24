"""Flyweight / Memoization & Object Cache Pattern Detection Rule."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import PatternType


class FlyweightPatternRule(BasePatternRule):
    """Detects Flyweight / Memoization and Shared Object Cache pattern instances in Clojure.

    Indicators:
    - Usage of `memoize` to cache and share immutable computation results/objects.
    - Global definition binding holding a `memoize` wrapper over an expensive calculation.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.FLYWEIGHT

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        detections.extend(self._detect_state_memoize(model))
        detections.extend(self._detect_fn_memoize(model))
        detections.extend(self._detect_oop_flyweights(model))
        return detections

    def _detect_state_memoize(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for state in model.all_states():
            if state.initial_expr and "memoize" in state.initial_expr:
                evidences = [
                    self.evidence(
                        description=f"State '{state.name}' shares and caches fine-grained immutable instances using 'memoize'",
                        weight=0.70,
                        location=state.location,
                        code_suffix="MEMOIZE_CACHE",
                    ),
                ]
                results.append(
                    self.create_detection(
                        target_name=state.name,
                        target_kind="memoized_flyweight_cache",
                        evidences=evidences,
                        primary_location=state.location,
                        related_locations=[],
                        summary=f"Flyweight pattern: '{state.name}' caches and shares immutable instances to eliminate redundant allocations",
                        base_score=0.25,
                    )
                )
        return results

    def _detect_fn_memoize(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for fn in model.all_functions():
            if "memoize" in fn.calls or "clojure.core/memoize" in fn.calls:
                evidences = [
                    self.evidence(
                        description=f"Function '{fn.name}' employs 'memoize' caching to share fine-grained computed objects",
                        weight=0.65,
                        location=fn.location,
                        code_suffix="FN_MEMOIZE_USAGE",
                    ),
                ]
                results.append(
                    self.create_detection(
                        target_name=fn.name,
                        target_kind="memoized_function",
                        evidences=evidences,
                        primary_location=fn.location,
                        related_locations=[],
                        summary=f"Flyweight pattern: function '{fn.name}' shares cached instances via memoization",
                        base_score=0.25,
                    )
                )
        return results

    def _detect_oop_flyweights(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for rec in model.all_records():
            if not rec.name.endswith(("Rule", "Test")):
                det = self._analyze_flyweight_record(rec)
                if det:
                    results.append(det)
        return results

    def _analyze_flyweight_record(self, rec: Any) -> Detection | None:
        if "flyweight" not in rec.name.lower():
            return None

        pool_fields = self._find_pool_fields(rec.fields)
        if not pool_fields:
            return None

        evidences = [
            self.evidence(
                description=f"Class '{rec.name}' participates in Flyweight pattern to share fine-grained state",
                weight=0.55,
                location=rec.location,
                code_suffix="FLYWEIGHT_CLASS_NAMING",
            ),
            self.evidence(
                description=f"Maintains flyweight instance pool/cache: {', '.join(pool_fields)}",
                weight=0.45,
                location=rec.location,
                code_suffix="FLYWEIGHT_POOL_FIELD",
            ),
        ]
        return self.create_detection(
            target_name=rec.name,
            target_kind="flyweight_class",
            evidences=evidences,
            primary_location=rec.location,
            related_locations=[],
            summary=f"Flyweight pattern: class '{rec.name}' shares fine-grained intrinsic state",
            base_score=0.35,
        )

    def _find_pool_fields(self, fields: list[str]) -> list[str]:
        keywords = ("flyweight", "pool", "cache", "map", "table")
        results = []
        for f in fields:
            f_lower = f.lower()
            if any(k in f_lower for k in keywords):
                results.append(f)
        return results
