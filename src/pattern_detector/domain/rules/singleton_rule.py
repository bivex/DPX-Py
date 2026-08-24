"""Singleton Pattern Detection Rule for C++."""

from __future__ import annotations

import re

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternCategory, PatternType, SourceLocation

_MEYERS_INSTANCE_RE = re.compile(r"\bstatic\s+([A-Za-z0-9_:]+)\s*(&|\*)\s*([A-Za-z0-9_]+)\s*\(")


class SingletonPatternRule(BasePatternRule):
    """Detects Singleton Pattern instances in C++.

    Indicators:
    - Meyers' Singleton: Static member function returning reference to local static instance
      (`static MyClass& getInstance() { static MyClass instance; return instance; }`).
    - Classic Static Pointer Singleton: Private static instance pointer with public accessor.
    - Deleted copy constructor / copy assignment operator (`MyClass(const MyClass&) = delete;`).
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.SINGLETON

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []

        # 1. State-backed Singletons (from AST extractor or static instances)
        for state in model.all_states():
            if not state.is_once:
                continue

            evidences: list[Evidence] = [
                self.evidence(
                    description=f"Static singleton instance managed for '{state.name}'",
                    weight=0.60,
                    location=state.location,
                    code_suffix="STATIC_SINGLETON_INSTANCE",
                )
            ]

            detection = self.create_detection(
                target_name=state.name,
                target_kind="static_singleton_state",
                evidences=evidences,
                primary_location=state.location,
                summary=f"Singleton pattern: static single-instance management for '{state.name}'",
                base_score=0.35,
            )
            detection.pattern_category = PatternCategory.CREATIONAL
            detections.append(detection)

        # 2. Inspect Records / Classes for Singleton Idioms
        for rec in model.all_records():
            evidences = []
            related_locs: list[SourceLocation] = []

            # Check methods for getInstance / get()
            get_instance_methods = [
                m for m in rec.methods
                if any(k in m.name.lower() for k in ("getinstance", "instance", "get_instance", "shared_instance"))
            ]

            if get_instance_methods:
                m = get_instance_methods[0]
                body = m.body_text or ""
                is_meyers = f"static {rec.name}" in body or "static auto" in body or "return instance" in body
                evidences.append(
                    self.evidence(
                        description=f"Class '{rec.name}' provides static singleton accessor method '{m.name}'"
                        + (" (Meyers' Singleton)" if is_meyers else ""),
                        weight=0.65 if is_meyers else 0.50,
                        location=m.location,
                        code_suffix="MEYERS_SINGLETON_ACCESSOR" if is_meyers else "SINGLETON_ACCESSOR",
                    )
                )
                related_locs.append(m.location)

            # Check static fields or instance pointers
            has_instance_field = any("instance" in f.lower() or f == rec.name for f in rec.fields)
            if has_instance_field:
                evidences.append(
                    self.evidence(
                        description=f"Class '{rec.name}' maintains static instance field",
                        weight=0.35,
                        location=rec.location,
                        code_suffix="STATIC_INSTANCE_FIELD",
                    )
                )

            if evidences and len(evidences) >= 1 and (get_instance_methods or has_instance_field):
                detection = self.create_detection(
                    target_name=rec.name,
                    target_kind="cpp_singleton_class",
                    evidences=evidences,
                    primary_location=rec.location,
                    related_locations=related_locs,
                    summary=f"Singleton pattern: class '{rec.name}' guarantees a single global instance",
                    base_score=0.35,
                )
                detection.pattern_category = PatternCategory.CREATIONAL
                detections.append(detection)

        return detections
