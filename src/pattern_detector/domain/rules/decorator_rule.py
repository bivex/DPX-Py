"""Decorator / Ring Middleware Pattern Detection Rule."""

from __future__ import annotations

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

        for fn in model.all_functions():
            # Skip records/multimethod dispatch branches
            if fn.is_multimethod or fn.parent_multimethod:
                continue

            evidences: list[Evidence] = []
            related_locs: list[SourceLocation] = []

            has_handler_param = False
            handler_param_name = ""
            for params in fn.parameter_lists:
                for p in params:
                    p_lower = p.lower()
                    if p_lower in ("handler", "app", "f", "delegate", "wrapped", "next-handler"):
                        has_handler_param = True
                        handler_param_name = p
                        break
                if has_handler_param:
                    break

            is_wrap_naming = fn.name.startswith("wrap-") or fn.name.startswith("wrap_") or "middleware" in fn.name.lower()

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

            # Check if function calls handler inside body or composes
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

            # If evidence is sufficient to consider it a decorator/middleware
            if evidences and (len(evidences) >= 2 or (fn.returns_closure and has_handler_param) or (is_wrap_naming and fn.returns_closure)):
                detections.append(
                    self.create_detection(
                        target_name=fn.name,
                        target_kind="middleware_decorator",
                        evidences=evidences,
                        primary_location=fn.location,
                        related_locations=related_locs,
                        summary=f"Decorator pattern: Ring-style middleware function '{fn.name}' wrapping request handler",
                        base_score=0.10,
                    )
                )

        # 2. C++ OOP Decorator Pattern (Wrapping Component interface)
        for rec in model.all_records():
            name_lower = rec.name.lower()
            is_decorator_named = "decorator" in name_lower

            # Check if implements a component protocol
            implemented_protocols = [
                proto.name for proto in model.all_protocols()
                if rec.implements_protocol(proto.name) or any(r.name == rec.name for r in model.find_records_implementing(proto.name))
            ]

            # Check for wrapped component field matching the same interface or 'component'
            component_fields = [
                f for f in rec.fields
                if any(k in f.lower() for k in ("component", "wrapped", "decoratee"))
                or any(p.lower() in f.lower() for p in implemented_protocols)
            ]

            # Exclude non-decorator GoF roles when class is not explicitly named Decorator
            if not is_decorator_named and any(
                k in name_lower for k in ("flyweight", "observer", "subject", "mediator", "proxy", "bridge", "abstraction", "state", "command", "strategy", "visitor")
            ):
                continue

            if (is_decorator_named and (implemented_protocols or component_fields)) or (implemented_protocols and component_fields):
                evidences = []
                related_locs = []

                if is_decorator_named:
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

                detections.append(
                    self.create_detection(
                        target_name=rec.name,
                        target_kind="cpp_decorator_class",
                        evidences=evidences,
                        primary_location=rec.location,
                        related_locations=related_locs,
                        summary=f"Decorator pattern: class '{rec.name}' dynamically augments component behavior via wrapping",
                        base_score=0.30,
                    )
                )

        return detections
