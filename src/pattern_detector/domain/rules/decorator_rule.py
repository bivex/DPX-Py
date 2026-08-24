"""Decorator / Ring Middleware Pattern Detection Rule."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternType, SourceLocation


class DecoratorPatternRule(BasePatternRule):
    """Detects Decorator / Middleware Pattern instances in Clojure.

    Indicators:
    - Middleware function returning an inner closure `(fn [req] ...)` wrapping the wrapped handler.
    - Function accepting a `handler` / `app` / `delegate` / `f` argument and invoking it inside its body.
    - Middleware naming convention (`wrap-*` / `with-*`).
    - Handlers composed via `comp`.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.DECORATOR

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        detections.extend(self._detect_functional_decorators(model))
        detections.extend(self._detect_oop_decorators(model))
        return detections

    def _detect_functional_decorators(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for fn in model.all_functions():
            if not fn.is_multimethod and not fn.parent_multimethod:
                det = self._analyze_functional_decorator(fn)
                if det:
                    results.append(det)
        return results

    def _analyze_functional_decorator(self, fn: Any) -> Detection | None:
        has_handler_param, handler_param_name = self._find_handler_param(fn)
        is_wrap_naming = fn.name.startswith(("wrap-", "wrap_")) or "middleware" in fn.name.lower()

        evidences = self._build_functional_decorator_evidences(
            fn, has_handler_param, handler_param_name, is_wrap_naming
        )
        if not self._is_functional_decorator(evidences, fn.returns_closure, has_handler_param, is_wrap_naming):
            return None

        return self.create_detection(
            target_name=fn.name,
            target_kind="middleware_decorator",
            evidences=evidences,
            primary_location=fn.location,
            related_locations=[],
            summary=f"Decorator pattern: Ring-style middleware function '{fn.name}' wrapping request handler",
            base_score=0.10,
        )

    def _find_handler_param(self, fn: Any) -> tuple[bool, str]:
        valid_names = ("handler", "app", "f", "delegate", "wrapped", "next-handler")
        for params in fn.parameter_lists:
            for p in params:
                if p.lower() in valid_names:
                    return True, p
        return False, ""

    def _is_functional_decorator(
        self, evidences: list[Evidence], returns_closure: bool, has_param: bool, is_wrap: bool
    ) -> bool:
        if not evidences:
            return False
        return len(evidences) >= 2 or (returns_closure and has_param) or (is_wrap and returns_closure)

    def _build_functional_decorator_evidences(
        self, fn: Any, has_handler_param: bool, handler_param_name: str, is_wrap_naming: bool
    ) -> list[Evidence]:
        evidences: list[Evidence] = []
        if has_handler_param:
            evidences.append(
                self.evidence(
                    description=f"Function accepts a wrapped handler parameter '{handler_param_name}'",
                    weight=0.40,
                    location=fn.location,
                    code_suffix="HANDLER_PARAMETER",
                )
            )
        if fn.returns_closure:
            evidences.append(
                self.evidence(
                    description="Function returns an inner closure/function (fn [req ...] ...) decorating execution",
                    weight=0.45,
                    location=fn.location,
                    code_suffix="RETURNS_CLOSURE",
                )
            )
        if is_wrap_naming:
            evidences.append(
                self.evidence(
                    description=f"Follows idiomatic Clojure/Ring middleware decorator naming convention '{fn.name}'",
                    weight=0.35,
                    location=fn.location,
                    code_suffix="MIDDLEWARE_NAMING",
                )
            )
        if handler_param_name and handler_param_name in fn.calls:
            evidences.append(
                self.evidence(
                    description=f"Explicitly delegates execution to the wrapped handler '{handler_param_name}'",
                    weight=0.30,
                    location=fn.location,
                    code_suffix="DELEGATES_TO_HANDLER",
                )
            )
        if any(call in ("comp", "clojure.core/comp") for call in fn.calls):
            evidences.append(
                self.evidence(
                    description="Uses function composition (comp) to chain decorator/middleware layers",
                    weight=0.25,
                    location=fn.location,
                    code_suffix="COMP_COMPOSITION",
                )
            )
        return evidences

    def _detect_oop_decorators(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for rec in model.all_records():
            if not rec.name.endswith(("Rule", "Test")):
                det = self._analyze_decorator_record(rec, model)
                if det:
                    results.append(det)
        return results

    def _analyze_decorator_record(self, rec: Any, model: CodeModel) -> Detection | None:
        name_lower = rec.name.lower()
        is_decorator_named = "decorator" in name_lower
        if not is_decorator_named and self._is_excluded_gof_name(name_lower):
            return None

        implemented_protocols = self._find_implemented_protocols(rec, model)
        component_fields = self._find_decorator_component_fields(rec.fields, implemented_protocols)

        if not (implemented_protocols and component_fields):
            return None

        evidences, related_locs = self._build_oop_decorator_evidences(
            rec, model, is_decorator_named, implemented_protocols, component_fields
        )
        return self.create_detection(
            target_name=rec.name,
            target_kind="decorator_class",
            evidences=evidences,
            primary_location=rec.location,
            related_locations=related_locs,
            summary=f"Decorator pattern: class '{rec.name}' dynamically augments component behavior via wrapping",
            base_score=0.30,
        )

    def _is_excluded_gof_name(self, name_lower: str) -> bool:
        excluded = (
            "flyweight",
            "observer",
            "subject",
            "mediator",
            "proxy",
            "bridge",
            "abstraction",
            "state",
            "command",
            "strategy",
            "visitor",
        )
        return any(k in name_lower for k in excluded)

    def _find_implemented_protocols(self, rec: Any, model: CodeModel) -> list[str]:
        results = []
        for proto in model.all_protocols():
            if rec.implements_protocol(proto.name) or any(
                r.name == rec.name for r in model.find_records_implementing(proto.name)
            ):
                results.append(proto.name)
        return results

    def _find_decorator_component_fields(self, fields: list[str], implemented_protocols: list[str]) -> list[str]:
        results = []
        for f in fields:
            f_lower = f.lower()
            if any(k in f_lower for k in ("component", "wrapped", "decoratee")) or any(
                p.lower() in f_lower for p in implemented_protocols
            ):
                results.append(f)
        return results

    def _build_oop_decorator_evidences(
        self,
        rec: Any,
        model: CodeModel,
        is_named: bool,
        implemented_protocols: list[str],
        component_fields: list[str],
    ) -> tuple[list[Evidence], list[SourceLocation]]:
        evidences: list[Evidence] = []
        related_locs: list[SourceLocation] = []

        if is_named:
            evidences.append(
                self.evidence(
                    description=f"Class '{rec.name}' follows Decorator pattern naming convention",
                    weight=0.50,
                    location=rec.location,
                    code_suffix="DECORATOR_NAMING",
                )
            )
        if implemented_protocols:
            evidences.append(
                self.evidence(
                    description=f"Implements decorated component interface(s): {', '.join(implemented_protocols)}",
                    weight=0.45,
                    location=rec.location,
                    code_suffix="DECORATOR_IMPLEMENTS_COMPONENT",
                )
            )
            for p_name in implemented_protocols:
                proto = model.find_protocol(p_name)
                if proto:
                    related_locs.append(proto.location)

        if component_fields:
            evidences.append(
                self.evidence(
                    description=f"Maintains wrapped component reference field(s): {', '.join(component_fields)}",
                    weight=0.45,
                    location=rec.location,
                    code_suffix="DECORATOR_WRAPPED_FIELD",
                )
            )

        return evidences, related_locs
