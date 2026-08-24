"""Single Responsibility Principle (SRP) Detection Rule."""

from __future__ import annotations

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternCategory, PatternType


class SingleResponsibilityRule(BasePatternRule):
    """Detects violations and adherences to the Single Responsibility Principle (SRP).

    Indicators:
    - God Object / Blob: Class with excessive methods (>10), high field count, and mixed concerns
      (e.g. database access + HTTP handling + JSON serialization + business computation).
    - Single-focus cohesive classes adhering strictly to SRP.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.SINGLE_RESPONSIBILITY

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []

        concern_keywords = {
            "persistence": ("save", "find", "delete", "query", "insert", "update", "repository", "dao", "db"),
            "http_web": ("handle", "request", "response", "get", "post", "endpoint", "controller", "route"),
            "serialization": ("json", "xml", "serialize", "deserialize", "parse", "format"),
            "auth_security": ("authenticate", "authorize", "token", "password", "crypto", "hash", "session"),
            "business_logic": ("calculate", "compute", "process", "validate", "execute", "apply"),
        }

        for rec in model.all_records():
            if rec.name.endswith("Test") or rec.name.endswith("Tests"):
                continue

            # Exclude plain getters, setters, equals, hashCode, toString
            business_methods = [
                m for m in rec.methods
                if not m.name.split(".")[-1].startswith(("get", "set", "is", "has"))
                and m.name.split(".")[-1] not in ("equals", "hashcode", "tostring")
            ]
            method_names = [m.name.split(".")[-1].lower() for m in business_methods]
            fields_count = len(rec.fields)
            methods_count = len(business_methods)

            # Identify detected concern categories
            matched_concerns: dict[str, list[str]] = {}
            for concern, kws in concern_keywords.items():
                matching = [m for m in method_names if any(kw in m for kw in kws)]
                if matching:
                    matched_concerns[concern] = matching

            evidences: list[Evidence] = []

            # 1. God Object / Mixed Concerns Violation
            if len(matched_concerns) >= 3 or (methods_count >= 12 and len(matched_concerns) >= 2):
                concerns_str = ", ".join(f"{c} ({len(ms)} methods)" for c, ms in matched_concerns.items())
                evidences.append(
                    self.evidence(
                        description=f"Class '{rec.name}' mixes {len(matched_concerns)} disparate concerns ({concerns_str}), violating SRP",
                        weight=min(0.60, 0.30 + 0.10 * len(matched_concerns)),
                        location=rec.location,
                        code_suffix="SRP_MIXED_CONCERNS",
                    )
                )

                if methods_count >= 10:
                    evidences.append(
                        self.evidence(
                            description=f"High method count ({methods_count} methods) indicates bloated class responsibility",
                            weight=min(0.40, 0.20 + 0.02 * methods_count),
                            location=rec.location,
                            code_suffix="SRP_HIGH_METHOD_COUNT",
                        )
                    )

                if fields_count >= 6:
                    evidences.append(
                        self.evidence(
                            description=f"High field count ({fields_count} fields) suggests multi-purpose state holder",
                            weight=0.25,
                            location=rec.location,
                            code_suffix="SRP_HIGH_FIELD_COUNT",
                        )
                    )

                detections.append(
                    self.create_detection(
                        target_name=rec.name,
                        target_kind="god_class_srp_violation",
                        evidences=evidences,
                        primary_location=rec.location,
                        summary=f"SRP Violation (God Class): '{rec.name}' mixes {len(matched_concerns)} concerns across {methods_count} methods",
                        base_score=0.40,
                    )
                )
                # Assign PRINCIPLE category
                detections[-1].pattern_category = PatternCategory.PRINCIPLE

        return detections
