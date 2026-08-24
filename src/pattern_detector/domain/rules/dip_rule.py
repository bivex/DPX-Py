"""Dependency Inversion Principle (DIP) Detection Rule for Python."""

from __future__ import annotations

import re

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import PatternCategory, PatternType

_NEW_EXPR_RE = re.compile(
    r"\b(?:new\s+([A-Za-z0-9_]+)|std::make_unique<([A-Za-z0-9_]+)>|std::make_shared<([A-Za-z0-9_]+)>)"
)
_PYTHON_CONSTRUCTOR_RE = re.compile(r"\b([A-Z][A-Za-z0-9_]+)\s*\(")


from typing import Any


class DependencyInversionRule(BasePatternRule):
    """Detects violations and adherences to the Dependency Inversion Principle (DIP) in Python.

    Indicators:
    - DIP Adherence: High-level class depends on injected abstract base class / Protocol (types, constructor args).
    - DIP Violation: High-level business service directly instantiates concrete low-level infrastructure
      classes (e.g. `MySqlDatabase()`, `FileLogger()`) inside its body or constructors.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.DEPENDENCY_INVERSION

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        protocols_names = {p.name for p in model.all_protocols()}

        for rec in model.all_records():
            if not rec.name.endswith(("Rule", "Test")) and len(rec.methods) > 0:
                det = self._analyze_record_dip(rec, protocols_names)
                if det:
                    detections.append(det)

        return detections

    def _analyze_record_dip(self, rec: Any, protocols_names: set[str]) -> Detection | None:
        interface_deps = self._find_interface_deps(rec, protocols_names)
        concrete_instantiations = self._find_concrete_instantiations(rec)

        if concrete_instantiations and any(sfx in rec.name for sfx in ("Service", "Controller", "UseCase", "Manager")):
            unique_news = sorted(set(concrete_instantiations))
            evidences = [
                self.evidence(
                    description=f"Class '{rec.name}' directly instantiates concrete dependencies ({', '.join(unique_news)}), violating DIP",
                    weight=0.60,
                    location=rec.location,
                    code_suffix="DIP_HARDCODED_CONCRETE_INSTANTIATION",
                ),
                self.evidence(
                    description="High-level modules should depend on abstract Protocols/ABCs, not direct concrete class instantiations",
                    weight=0.35,
                    location=rec.location,
                    code_suffix="DIP_INVERSION_REQUIRED",
                ),
            ]
            detection = self.create_detection(
                target_name=rec.name,
                target_kind="dip_concrete_coupling",
                evidences=evidences,
                primary_location=rec.location,
                summary=f"DIP Violation: High-level '{rec.name}' directly creates concrete classes: {', '.join(unique_news)}",
                base_score=0.35,
            )
            detection.pattern_category = PatternCategory.PRINCIPLE
            return detection

        if interface_deps:
            unique_deps = sorted(set(interface_deps))
            evidences = [
                self.evidence(
                    description=f"Class '{rec.name}' depends on abstracted interface(s): {', '.join(unique_deps)} adhering to DIP",
                    weight=0.60,
                    location=rec.location,
                    code_suffix="DIP_INJECTED_ABSTRACTION",
                ),
                self.evidence(
                    description="Core domain logic is decoupled from infrastructure details via Dependency Injection",
                    weight=0.35,
                    location=rec.location,
                    code_suffix="DIP_DECOUPLED_ARCHITECTURE",
                ),
            ]
            detection = self.create_detection(
                target_name=rec.name,
                target_kind="dip_interface_dependency",
                evidences=evidences,
                primary_location=rec.location,
                summary=f"DIP Adherence: '{rec.name}' depends on interface abstraction(s) ({', '.join(unique_deps)})",
                base_score=0.35,
            )
            detection.pattern_category = PatternCategory.PRINCIPLE
            return detection

        return None

    def _find_interface_deps(self, rec: Any, protocols_names: set[str]) -> list[str]:
        interface_deps: list[str] = []
        for f in rec.fields:
            f_norm = f.lower().lstrip("_")
            for proto_name in protocols_names:
                p_norm = proto_name.lower().lstrip("i")
                if f_norm in (p_norm, proto_name.lower(), f"{p_norm}_service", f"{p_norm}_port"):
                    interface_deps.append(proto_name)
        return interface_deps

    def _find_concrete_instantiations(self, rec: Any) -> list[str]:
        concrete: list[str] = []
        for m in rec.methods:
            if m.name.split(".")[-1] not in ("__init__", "__post_init__"):
                found = self._extract_method_concrete_deps(m, rec.name)
                concrete.extend(found)
        return concrete

    def _extract_method_concrete_deps(self, m: Any, rec_name: str) -> list[str]:
        body = m.body_text or ""
        suffixes = ("Repository", "Client", "Database", "Dao", "Gateway")
        new_deps = self._extract_new_expr_concrete_deps(body, suffixes)
        ctor_deps = self._extract_constructor_concrete_deps(body, m.calls, rec_name, suffixes)
        return new_deps + ctor_deps

    def _extract_new_expr_concrete_deps(self, body: str, suffixes: tuple[str, ...]) -> list[str]:
        results: list[str] = []
        for raw_match in _NEW_EXPR_RE.findall(body):
            cl = raw_match[0] if isinstance(raw_match, tuple) and raw_match else str(raw_match)
            if cl.endswith(suffixes):
                results.append(cl)
        return results

    def _extract_constructor_concrete_deps(
        self, body: str, calls: list[str], rec_name: str, suffixes: tuple[str, ...]
    ) -> list[str]:
        results: list[str] = []
        candidates = _PYTHON_CONSTRUCTOR_RE.findall(body) + calls
        for cl in candidates:
            if cl.endswith(suffixes) and cl != rec_name:
                results.append(cl)
        return results
