"""Domain Service for coordinating pattern detection rules on a CodeModel."""

from __future__ import annotations

import time
from collections.abc import Sequence

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection, DetectionReport
from pattern_detector.domain.rules import get_default_rules
from pattern_detector.domain.rules.base import PatternRule
from pattern_detector.domain.value_objects import PatternType


class PatternDetectorService:
    """Domain service that applies configured pattern rules to a CodeModel."""

    def __init__(self, rules: Sequence[PatternRule] | None = None) -> None:
        self._rules: list[PatternRule] = list(rules) if rules is not None else get_default_rules()

    @property
    def rules(self) -> list[PatternRule]:
        return list(self._rules)

    def add_rule(self, rule: PatternRule) -> None:
        self._rules.append(rule)

    def detect_all(self, model: CodeModel, project_path: str = "") -> DetectionReport:
        """Run all configured detection rules against the CodeModel and build a DetectionReport."""
        start_time = time.perf_counter()
        all_detections: list[Detection] = []

        for rule in self._rules:
            rule_detections = rule.detect(model)
            all_detections.extend(rule_detections)

        elapsed = time.perf_counter() - start_time

        # Disambiguate overlapping pattern classifications
        disambiguated = self._disambiguate_detections(all_detections)

        # Sort detections by confidence score descending
        disambiguated.sort(key=lambda d: d.confidence.score, reverse=True)

        scanned_files_count = len(model.all_file_paths()) or len(model.namespaces)

        return DetectionReport(
            project_path=project_path,
            scanned_files_count=scanned_files_count,
            detections=disambiguated,
            elapsed_seconds=elapsed,
        )

    def _disambiguate_detections(self, detections: list[Detection]) -> list[Detection]:
        """Disambiguates and deduplicates overlapping pattern detections based on structural specificity."""
        claimed_targets: dict[str, set[PatternType]] = {}
        for d in detections:
            claimed_targets.setdefault(d.target_name, set()).add(d.pattern_type)

        return [d for d in detections if self._should_keep_detection(d, claimed_targets)]

    def _should_keep_detection(self, d: Detection, claimed_targets: dict[str, set[PatternType]]) -> bool:
        target_lower = d.target_name.lower()
        other_patterns = claimed_targets.get(d.target_name, set()) - {d.pattern_type}

        if d.pattern_type == PatternType.STRATEGY and self._is_dominated_strategy(other_patterns, target_lower):
            return False
        return not self._is_conflicting_factory_or_command(d.pattern_type, other_patterns, target_lower)

    def _is_dominated_strategy(self, other_patterns: set[PatternType], target_lower: str) -> bool:
        competing = (
            PatternType.COMPOSITE,
            PatternType.VISITOR,
            PatternType.OBSERVER,
            PatternType.COMMAND,
            PatternType.STATE,
            PatternType.BRIDGE,
            PatternType.BUILDER,
            PatternType.ABSTRACT_FACTORY,
            PatternType.FACTORY_METHOD,
            PatternType.PROTOTYPE,
            PatternType.FLYWEIGHT,
            PatternType.MEDIATOR,
            PatternType.ITERATOR,
            PatternType.CHAIN_OF_RESPONSIBILITY,
            PatternType.ADAPTER,
            PatternType.PROXY,
            PatternType.DECORATOR,
        )
        if any(p in other_patterns for p in competing):
            return True

        non_strategy = (
            "product",
            "element",
            "subject",
            "prototype",
            "flyweight",
            "visitor",
            "observer",
            "listener",
            "state",
            "command",
            "builder",
            "factory",
            "creator",
            "mediator",
            "iterator",
            "handler",
            "component",
            "implementor",
            "adapter",
            "proxy",
            "decorator",
            "memento",
        )
        is_other_role = any(k in target_lower for k in non_strategy)
        is_explicit_strategy = any(k in target_lower for k in ("strategy", "algorithm", "policy"))
        return is_other_role and not is_explicit_strategy

    def _is_conflicting_factory_or_command(
        self, p_type: PatternType, other_patterns: set[PatternType], target_lower: str
    ) -> bool:
        if p_type == PatternType.ABSTRACT_FACTORY and ("builder" in target_lower or target_lower == "creator"):
            return True
        if p_type == PatternType.FACTORY_METHOD and (
            PatternType.ABSTRACT_FACTORY in other_patterns or "abstract" in target_lower
        ):
            return True
        return p_type == PatternType.COMMAND and ("abstraction" in target_lower or "component" in target_lower)
