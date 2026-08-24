"""Don't Repeat Yourself (DRY) Principle Detection Rule."""

from __future__ import annotations

import re
from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import PatternCategory, PatternType

_WHITESPACE_RE = re.compile(r"\s+")
_COMMENT_RE = re.compile(r"(?://|#).*")


class DryRule(BasePatternRule):
    """Detects structural code duplication violating the DRY (Don't Repeat Yourself) principle.

    Indicators:
    - Duplicate Method Bodies: Substantial identical non-trivial method bodies across different classes
      (length >= 4 non-empty lines).
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.DRY

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        body_map = self._collect_normalized_bodies(model)

        for instances in body_map.values():
            unique_instances = self._deduplicate_instances(instances)
            if len(unique_instances) >= 2 and len({name for name, _ in unique_instances}) >= 2:
                detections.append(self._create_dry_detection(unique_instances))

        return detections

    def _collect_normalized_bodies(self, model: CodeModel) -> dict[str, list[tuple[str, Any]]]:
        body_map: dict[str, list[tuple[str, Any]]] = {}
        for fn in model.all_functions():
            simple_name = fn.name.split("::")[-1].split(".")[-1]
            if simple_name.startswith(("get", "set", "is", "has")) or simple_name in (
                "toString",
                "hashCode",
                "equals",
                "compareTo",
                "__str__",
                "__repr__",
                "__init__",
            ):
                continue
            body = (fn.body_text or "").strip()
            norm_body = _WHITESPACE_RE.sub(" ", _COMMENT_RE.sub("", body)).strip()
            if len(norm_body) >= 50 and "return" in norm_body:
                body_map.setdefault(norm_body, []).append((fn.name, fn.location))
        return body_map

    def _deduplicate_instances(self, instances: list[tuple[str, Any]]) -> list[tuple[str, Any]]:
        unique_instances = []
        seen_locs = set()
        for name, loc in instances:
            loc_key = (name, loc.file_path, loc.line)
            if loc_key not in seen_locs:
                seen_locs.add(loc_key)
                unique_instances.append((name, loc))
        return unique_instances

    def _create_dry_detection(self, unique_instances: list[tuple[str, Any]]) -> Detection:
        names = [name for name, _ in unique_instances]
        locs = [loc for _, loc in unique_instances]
        evidences = [
            self.evidence(
                description=f"Identical duplicate code logic detected across {len(unique_instances)} methods: {', '.join(names)}",
                weight=min(0.70, 0.45 + 0.10 * len(unique_instances)),
                location=locs[0],
                code_suffix="DRY_CODE_DUPLICATION",
            ),
            self.evidence(
                description="Duplicate logic creates maintenance hazards when business rules change; extract into shared utility or base class",
                weight=0.35,
                location=locs[1],
                code_suffix="DRY_EXTRACTION_RECOMMENDED",
            ),
        ]
        detection = self.create_detection(
            target_name=names[0],
            target_kind="dry_code_duplication",
            evidences=evidences,
            primary_location=locs[0],
            related_locations=locs[1:],
            summary=f"DRY Violation: Duplicate logic shared across {len(unique_instances)} methods ({', '.join(names)})",
            base_score=0.40,
        )
        detection.pattern_category = PatternCategory.PRINCIPLE
        return detection
