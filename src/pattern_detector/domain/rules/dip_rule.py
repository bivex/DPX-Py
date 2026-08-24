"""Dependency Inversion Principle (DIP) Detection Rule for Python."""

from __future__ import annotations

import re

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import PatternCategory, PatternType

_NEW_EXPR_RE = re.compile(r"\b(?:new\s+([A-Za-z0-9_]+)|std::make_unique<([A-Za-z0-9_]+)>|std::make_shared<([A-Za-z0-9_]+)>)")
_PYTHON_CONSTRUCTOR_RE = re.compile(r"\b([A-Z][A-Za-z0-9_]+)\s*\(")


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
            # Check fields and constructor injection
            interface_deps: list[str] = []
            for f in rec.fields:
                # If a field name matches an interface name or convention
                for proto_name in protocols_names:
                    if proto_name.lower() in f.lower() or f.lower() in proto_name.lower():
                        interface_deps.append(proto_name)

            # Check direct instantiation of low-level dependencies inside methods
            concrete_instantiations: list[str] = []
            for m in rec.methods:
                body = m.body_text or ""
                matches = _NEW_EXPR_RE.findall(body)
                py_matches = _PYTHON_CONSTRUCTOR_RE.findall(body)
                for raw_match in matches:
                    cl = next((item for item in raw_match if item), "")
                    if any(cl.endswith(sfx) for sfx in ("Repository", "Service", "Client", "Database", "Dao", "Gateway", "Sender")):
                        concrete_instantiations.append(cl)
                for cl in py_matches + m.calls:
                    if any(cl.endswith(sfx) for sfx in ("Repository", "Service", "Client", "Database", "Dao", "Gateway", "Sender")) and cl != rec.name:
                        concrete_instantiations.append(cl)

            # 1. DIP Violation: Hardcoded concrete infrastructure dependencies
            if concrete_instantiations and ("Service" in rec.name or "Controller" in rec.name or "Manager" in rec.name):
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
                detections.append(detection)

            # 2. DIP Adherence: Clean abstraction injection
            elif interface_deps:
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
                detections.append(detection)

        return detections
