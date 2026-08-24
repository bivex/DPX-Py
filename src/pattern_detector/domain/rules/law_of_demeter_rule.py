"""Law of Demeter (Principle of Least Knowledge) Detection Rule."""

from __future__ import annotations

import re

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import PatternCategory, PatternType

_CHAIN_CALL_RE = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)){2,})")


class LawOfDemeterRule(BasePatternRule):
    """Detects violations of the Law of Demeter (Principle of Least Knowledge).

    Indicators:
    - Train Wreck Calls: Multiple chained method calls navigating internal object graphs
      (e.g. `order.getCustomer().getAddress().getCity().toLowerCase()` with depth >= 3).
    - Excludes fluent builders or Stream API calls (filter, map, collect).
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.LAW_OF_DEMETER

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []

        # Fluent / Stream / String / Collection / Time API exclusions
        fluent_keywords = {
            "stream", "filter", "map", "flatmap", "collect", "reduce", "foreach", "findfirst", "findany",
            "builder", "build", "append", "then", "tostring", "trim", "strip", "substring", "replace",
            "valueof", "ofnullable", "orelse", "orelseget", "orelsethrow", "ifpresent", "ispresent",
            "when", "thenreturn", "thenthrow", "verify", "assertthat", "isequalto", "isnotnull", "istrue",
            "status", "header", "headers", "body", "ok", "badrequest", "created", "accepted", "notfound",
            "add", "multiply", "divide", "subtract", "setscale", "plus", "minus", "now", "of", "format",
            "parse", "join", "equals", "hashcode", "compareto", "contains", "contentequals", "startswith",
            "endswith", "matches", "indexof", "length", "isempty", "isblank", "isafter", "isbefore",
            "isequal", "iterator", "next", "hasnext", "getclass", "getname", "getsimplename",
            "tolowercase", "touppercase", "addall", "put", "putall", "remove", "clear", "resources",
            "registerpattern", "registerhints", "registertype",
        }

        for fn in model.all_functions():
            body = fn.body_text or ""
            # Look for expressions with chained method invocations: expr.m1().m2().m3()
            matches = _CHAIN_CALL_RE.finditer(body)

            for match in matches:
                chain_snippet = match.group(1).strip()
                # Split chained calls
                parts = [p.split("(")[0].strip() for p in chain_snippet.split(".") if p.strip()]

                # Filter out fluent stream and builder calls
                is_fluent = any(
                    p.lower() in fluent_keywords or p.lower().startswith(("with", "builder"))
                    for p in parts[1:]  # only check method names, not initial target variable
                )

                if not is_fluent and len(parts) >= 3:
                    evidences = [
                        self.evidence(
                            description=f"Method '{fn.name}' violates Law of Demeter with deep chained call: '{chain_snippet}'",
                            weight=min(0.65, 0.40 + 0.08 * len(parts)),
                            location=fn.location,
                            code_suffix="LOD_TRAIN_WRECK_CHAIN",
                        ),
                        self.evidence(
                            description="Navigating internal object structures breaks encapsulation and couples caller to indirect dependencies",
                            weight=0.35,
                            location=fn.location,
                            code_suffix="LOD_STRUCTURAL_COUPLING",
                        ),
                    ]

                    detection = self.create_detection(
                        target_name=fn.name,
                        target_kind="law_of_demeter_train_wreck",
                        evidences=evidences,
                        primary_location=fn.location,
                        summary=f"Law of Demeter Violation in '{fn.name}': deep chain '{chain_snippet}'",
                        base_score=0.35,
                    )
                    detection.pattern_category = PatternCategory.PRINCIPLE
                    detections.append(detection)

        return detections
