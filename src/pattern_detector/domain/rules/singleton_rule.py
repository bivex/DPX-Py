"""Singleton Pattern Detection Rule for Python."""

from __future__ import annotations

import re

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternCategory, PatternType, SourceLocation

_MEYERS_INSTANCE_RE = re.compile(r"\bstatic\s+([A-Za-z0-9_:]+)\s*(&|\*)\s*([A-Za-z0-9_]+)\s*\(")


from typing import Any


class SingletonPatternRule(BasePatternRule):
    """Detects Singleton Pattern instances in Python.

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
        detections.extend(self._detect_state_singletons(model))
        detections.extend(self._detect_record_singletons(model))
        return detections

    def _detect_state_singletons(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for state in model.all_states():
            if state.is_once:
                evidences = [
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
                results.append(detection)
        return results

    def _detect_record_singletons(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for rec in model.all_records():
            det = self._analyze_singleton_record(rec)
            if det:
                results.append(det)
        return results

    def _analyze_singleton_record(self, rec: Any) -> Detection | None:
        if rec.name.endswith(("Rule", "Test", "TestCase")):
            return None

        get_instance_methods = self._find_get_instance_methods(rec.methods)
        has_instance_field = any(self._is_singleton_instance_field(f, rec.name) for f in rec.fields)

        # Must have either a valid singleton accessor method, or a dedicated instance field with creation/new hook
        if not get_instance_methods and not (
            has_instance_field and any(m.name.split(".")[-1] in ("__new__", "get_instance", "instance") for m in rec.methods)
        ):
            return None

        evidences, related_locs = self._build_record_singleton_evidences(rec, get_instance_methods, has_instance_field)
        detection = self.create_detection(
            target_name=rec.name,
            target_kind="singleton_class",
            evidences=evidences,
            primary_location=rec.location,
            related_locations=related_locs,
            summary=f"Singleton pattern: class '{rec.name}' guarantees a single global instance",
            base_score=0.35,
        )
        detection.pattern_category = PatternCategory.CREATIONAL
        return detection

    def _is_singleton_instance_field(self, field_name: str, class_name: str) -> bool:
        fn = field_name.lower().strip()
        return fn in ("_instance", "__instance", "instance", "_instances", f"_{class_name.lower()}_instance", f"_{class_name.lower()}")

    def _find_get_instance_methods(self, methods: list[Any]) -> list[Any]:
        exact_accessors = {"getinstance", "get_instance", "shared_instance", "shared", "default_instance", "instance"}
        results = []
        for m in methods:
            base_name = m.name.split(".")[-1].lower()
            if base_name in exact_accessors or any(
                base_name.startswith(f"{k}_") for k in ("get_instance", "getinstance", "shared_instance")
            ):
                results.append(m)
        return results

    def _build_record_singleton_evidences(
        self, rec: Any, get_instance_methods: list[Any], has_instance_field: bool
    ) -> tuple[list[Evidence], list[SourceLocation]]:
        evidences: list[Evidence] = []
        related_locs: list[SourceLocation] = []

        if get_instance_methods:
            m = get_instance_methods[0]
            clean_name = m.name.split(".")[-1]
            body = m.body_text or ""
            is_meyers = f"static {rec.name}" in body or "static auto" in body or "return instance" in body
            suffix = " (Meyers' Singleton)" if is_meyers else ""
            evidences.append(
                self.evidence(
                    description=f"Class '{rec.name}' provides static singleton accessor method '{clean_name}'{suffix}",
                    weight=0.65 if is_meyers else 0.50,
                    location=m.location,
                    code_suffix="MEYERS_SINGLETON_ACCESSOR" if is_meyers else "SINGLETON_ACCESSOR",
                )
            )
            related_locs.append(m.location)

        if has_instance_field:
            evidences.append(
                self.evidence(
                    description=f"Class '{rec.name}' maintains static instance field",
                    weight=0.35,
                    location=rec.location,
                    code_suffix="STATIC_INSTANCE_FIELD",
                )
            )

        return evidences, related_locs
