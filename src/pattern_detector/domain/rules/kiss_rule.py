"""Keep It Simple, Stupid (KISS) Principle Detection Rule."""

from __future__ import annotations

import re

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import PatternCategory, PatternType

_BRANCH_RE = re.compile(r"\b(if|else if|while|for|switch|catch|case)\b")


class KissRule(BasePatternRule):
    """Detects violations of the KISS principle (excessive complexity).

    Indicators:
    - Long Parameter List: Methods taking > 5 parameters (should use parameter objects / DTOs).
    - High Cyclomatic Complexity / Deep Nesting: Methods with excessive branching keywords (if, while, for, switch, catch > 8).
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.KISS

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []

        for fn in model.all_functions():
            simple_name = fn.name.split(".")[-1]
            if simple_name in ("equals", "hashCode", "toString", "compareTo"):
                continue

            # 1. Parameter count check
            max_params = max((len(pl) for pl in fn.parameter_lists), default=0)
            if max_params >= 6:
                evidences = [
                    self.evidence(
                        description=f"Method '{fn.name}' has {max_params} parameters, violating KISS (Long Parameter List)",
                        weight=min(0.65, 0.40 + 0.05 * max_params),
                        location=fn.location,
                        code_suffix="KISS_LONG_PARAMETER_LIST",
                    ),
                    self.evidence(
                        description="Excessive parameters increase cognitive load and error probability; consider a Parameter Object / Builder",
                        weight=0.35,
                        location=fn.location,
                        code_suffix="KISS_PARAMETER_OBJECT_RECOMMENDED",
                    ),
                ]

                detection = self.create_detection(
                    target_name=fn.name,
                    target_kind="kiss_complexity_parameters",
                    evidences=evidences,
                    primary_location=fn.location,
                    summary=f"KISS Violation (Long Parameter List): Method '{fn.name}' takes {max_params} parameters",
                    base_score=0.35,
                )
                detection.pattern_category = PatternCategory.PRINCIPLE
                detections.append(detection)

            # 2. Control flow branching complexity check
            body = fn.body_text or ""
            branch_keywords = _BRANCH_RE.findall(body)
            if len(branch_keywords) >= 8:
                evidences = [
                    self.evidence(
                        description=f"Method '{fn.name}' has high cyclomatic complexity ({len(branch_keywords)} branch points), violating KISS",
                        weight=min(0.70, 0.40 + 0.04 * len(branch_keywords)),
                        location=fn.location,
                        code_suffix="KISS_HIGH_CYCLOMATIC_COMPLEXITY",
                    ),
                    self.evidence(
                        description="Complex nested conditionals are difficult to test and maintain; decompose into smaller functions",
                        weight=0.35,
                        location=fn.location,
                        code_suffix="KISS_DECOMPOSITION_NEEDED",
                    ),
                ]

                detection = self.create_detection(
                    target_name=fn.name,
                    target_kind="kiss_cyclomatic_complexity",
                    evidences=evidences,
                    primary_location=fn.location,
                    summary=f"KISS Violation (High Complexity): Method '{fn.name}' has {len(branch_keywords)} control flow branches",
                    base_score=0.40,
                )
                detection.pattern_category = PatternCategory.PRINCIPLE
                detections.append(detection)

        return detections
