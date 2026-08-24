"""Flyweight / Memoization & Object Cache Pattern Detection Rule."""

from __future__ import annotations

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

        # 1. State / Var definitions using memoize
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
                detections.append(
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

        # 2. Functions calling memoize
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
                detections.append(
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

        # 3. C++ OOP Flyweight Pattern (Flyweight Factory & Flyweight protocols)
        for rec in model.all_records():
            name_lower = rec.name.lower()
            if "flyweight" in name_lower:
                evidences = [
                    self.evidence(
                        description=f"Class '{rec.name}' participates in Flyweight pattern to share fine-grained state",
                        weight=0.55,
                        location=rec.location,
                        code_suffix="FLYWEIGHT_CLASS_NAMING",
                    )
                ]
                has_pool = any(
                    any(k in f.lower() for k in ("flyweight", "pool", "cache", "map", "table"))
                    for f in rec.fields
                )
                if has_pool:
                    evidences.append(
                        self.evidence(
                            description=f"Maintains flyweight instance pool/cache: {', '.join([f for f in rec.fields if any(k in f.lower() for k in ('flyweight', 'pool', 'cache', 'map', 'table'))])}",
                            weight=0.45,
                            location=rec.location,
                            code_suffix="FLYWEIGHT_POOL_FIELD",
                        )
                    )
                detections.append(
                    self.create_detection(
                        target_name=rec.name,
                        target_kind="cpp_flyweight_class",
                        evidences=evidences,
                        primary_location=rec.location,
                        related_locations=[],
                        summary=f"Flyweight pattern: class '{rec.name}' shares fine-grained intrinsic state",
                        base_score=0.35,
                    )
                )

        return detections
