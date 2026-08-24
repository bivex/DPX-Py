"""Chain of Responsibility / Processing Pipeline Pattern Detection Rule."""

from __future__ import annotations

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternType, SourceLocation


class ChainOfResponsibilityRule(BasePatternRule):
    """Detects Chain of Responsibility / Pipeline Pattern instances in Clojure.

    Indicators:
    - Pipeline assembly functions chaining 2+ middleware/handlers using `->`, `->>`, or `comp`.
    - Functions taking a request and passing it down a chain of handlers.
    - Router or pipeline compositions with multiple processing stages.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.CHAIN_OF_RESPONSIBILITY

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []

        for fn in model.all_functions():
            if fn.is_multimethod or fn.parent_multimethod:
                continue

            evidences: list[Evidence] = []
            related_locs: list[SourceLocation] = []

            # 1. Check for middleware calls in body
            middleware_calls = [
                c for c in fn.calls
                if c.startswith(("wrap-", "wrap_", "middleware-")) or "-middleware" in c
            ]

            # 2. Check for threading macros and composition
            has_threading = any(t in fn.body_text for t in ("->", "->>", "comp", "reduce"))
            has_comp = any(c in ("comp", "clojure.core/comp") for c in fn.calls)

            if middleware_calls:
                count = len(middleware_calls)
                evidences.append(
                    self.evidence(
                        description=f"Assembles pipeline chain of {count} middleware handlers: {', '.join(middleware_calls[:4])}",
                        weight=min(0.60, 0.30 + 0.10 * count),
                        location=fn.location,
                        code_suffix="MIDDLEWARE_CHAIN_CALLS",
                    )
                )

            if has_comp:
                evidences.append(
                    self.evidence(
                        description="Uses functional composition (comp) to chain multiple request processing handlers into a pipeline",
                        weight=0.35,
                        location=fn.location,
                        code_suffix="COMP_CHAIN",
                    )
                )

            if has_threading and middleware_calls:
                evidences.append(
                    self.evidence(
                        description="Uses threading pipeline (-> / ->>) to sequentially pass request context through chain stages",
                        weight=0.30,
                        location=fn.location,
                        code_suffix="THREADING_PIPELINE",
                    )
                )

            if len(middleware_calls) >= 2 or (len(middleware_calls) >= 1 and (has_comp or has_threading)):
                detections.append(
                    self.create_detection(
                        target_name=fn.name,
                        target_kind="middleware_pipeline",
                        evidences=evidences,
                        primary_location=fn.location,
                        related_locations=related_locs,
                        summary=f"Chain of Responsibility: pipeline '{fn.name}' chains {len(middleware_calls)} middleware processing stages",
                        base_score=0.20,
                    )
                )

        # 2. C++ OOP Chain of Responsibility Pattern (Handler chaining)
        for rec in model.all_records():
            name_lower = rec.name.lower()
            is_handler_named = "handler" in name_lower or "filter" in name_lower or "processor" in name_lower

            has_successor_field = any(
                any(k in f.lower() for k in ("successor", "next", "handler", "parent", "chain"))
                for f in rec.fields
            )
            has_chain_methods = any(
                any(k in m.name.lower() for k in ("setsuccessor", "setnext", "handle", "handlerequest", "process"))
                for m in rec.methods
            )

            if (is_handler_named and (has_successor_field or has_chain_methods)) or (has_successor_field and has_chain_methods):
                evidences = []
                if is_handler_named:
                    evidences.append(
                        self.evidence(
                            description=f"Class '{rec.name}' follows Chain of Responsibility handler naming convention",
                            weight=0.45,
                            location=rec.location,
                            code_suffix="HANDLER_CLASS_NAMING",
                        )
                    )
                if has_successor_field:
                    evidences.append(
                        self.evidence(
                            description=f"Maintains successor/next link to chain handler: {', '.join([f for f in rec.fields if any(k in f.lower() for k in ('successor', 'next', 'handler', 'parent', 'chain'))])}",
                            weight=0.45,
                            location=rec.location,
                            code_suffix="HANDLER_SUCCESSOR_FIELD",
                        )
                    )
                if has_chain_methods:
                    evidences.append(
                        self.evidence(
                            description=f"Declares request processing / successor configuration methods: {', '.join([m.name for m in rec.methods if any(k in m.name.lower() for k in ('setsuccessor', 'setnext', 'handle', 'handlerequest', 'process'))])}",
                            weight=0.40,
                            location=rec.location,
                            code_suffix="HANDLER_CHAIN_METHODS",
                        )
                    )

                detections.append(
                    self.create_detection(
                        target_name=rec.name,
                        target_kind="cpp_chain_handler",
                        evidences=evidences,
                        primary_location=rec.location,
                        related_locations=[],
                        summary=f"Chain of Responsibility: handler '{rec.name}' passes requests along dynamic chain of successor objects",
                        base_score=0.30,
                    )
                )

        return detections
