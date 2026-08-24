"""Single Responsibility Principle (SRP) Detection Rule."""

from __future__ import annotations

from typing import Any

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
        for rec in model.all_records():
            if not rec.name.endswith(("Test", "Tests")):
                det = self._analyze_record_srp(rec)
                if det:
                    detections.append(det)
        return detections

    def _analyze_record_srp(self, rec: Any) -> Detection | None:
        business_methods = [
            m
            for m in rec.methods
            if not m.name.split(".")[-1].startswith(("get", "set", "is", "has"))
            and m.name.split(".")[-1] not in ("equals", "hashcode", "tostring")
        ]
        method_names = [m.name.split(".")[-1].lower() for m in business_methods]
        matched_concerns = self._match_concerns(method_names)
        methods_count = len(business_methods)

        if not (len(matched_concerns) >= 3 or (methods_count >= 12 and len(matched_concerns) >= 2)):
            return None

        evidences = self._build_srp_evidences(rec, matched_concerns, methods_count, len(rec.fields))
        detection = self.create_detection(
            target_name=rec.name,
            target_kind="god_class_srp_violation",
            evidences=evidences,
            primary_location=rec.location,
            summary=f"SRP Violation (God Class): '{rec.name}' mixes {len(matched_concerns)} concerns across {methods_count} methods",
            base_score=0.40,
        )
        detection.pattern_category = PatternCategory.PRINCIPLE
        return detection

    def _match_concerns(self, method_names: list[str]) -> dict[str, list[str]]:
        concern_keywords = {
            "database_persistence": (
                "save_to_db",
                "insert_record",
                "execute_sql",
                "delete_from_db",
                "commit_tx",
                "query_db",
            ),
            "http_transport": (
                "http_get",
                "http_post",
                "send_request",
                "handle_request",
                "serve_route",
                "web_controller",
            ),
            "serialization": ("to_json", "from_json", "to_xml", "from_xml", "serialize_bytes", "deserialize_bytes"),
            "auth_security": (
                "authenticate_user",
                "verify_password",
                "generate_jwt",
                "encrypt_secret",
                "decrypt_secret",
            ),
            "billing_domain": ("process_payment", "calculate_tax", "charge_card", "refund_invoice", "apply_discount"),
        }
        matched: dict[str, list[str]] = {}
        for concern, kws in concern_keywords.items():
            matching = [m for m in method_names if any(kw in m for kw in kws)]
            if matching:
                matched[concern] = matching
        return matched

    def _build_srp_evidences(
        self, rec: Any, matched_concerns: dict[str, list[str]], methods_count: int, fields_count: int
    ) -> list[Evidence]:
        concerns_str = ", ".join(f"{c} ({len(ms)} methods)" for c, ms in matched_concerns.items())
        evidences = [
            self.evidence(
                description=f"Class '{rec.name}' mixes {len(matched_concerns)} disparate concerns ({concerns_str}), violating SRP",
                weight=min(0.60, 0.30 + 0.10 * len(matched_concerns)),
                location=rec.location,
                code_suffix="SRP_MIXED_CONCERNS",
            )
        ]
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
        return evidences
