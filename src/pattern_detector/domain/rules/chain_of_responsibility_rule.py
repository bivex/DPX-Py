"""Chain of Responsibility / Processing Pipeline Pattern Detection Rule."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternType


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
        detections.extend(self._detect_middleware_pipelines(model))
        detections.extend(self._detect_oop_handlers(model))
        return detections

    def _detect_middleware_pipelines(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for fn in model.all_functions():
            if not fn.is_multimethod and not fn.parent_multimethod:
                det = self._analyze_middleware_function(fn)
                if det:
                    results.append(det)
        return results

    def _analyze_middleware_function(self, fn: Any) -> Detection | None:
        middleware_calls = [
            c for c in fn.calls if c.startswith(("wrap-", "wrap_", "middleware-")) or "-middleware" in c
        ]
        has_threading = any(t in fn.body_text for t in ("->", "->>", "comp", "reduce"))
        has_comp = any(c in ("comp", "clojure.core/comp") for c in fn.calls)

        if not (len(middleware_calls) >= 2 or (len(middleware_calls) >= 1 and (has_comp or has_threading))):
            return None

        evidences = self._build_pipeline_evidences(fn, middleware_calls, has_comp, has_threading)
        return self.create_detection(
            target_name=fn.name,
            target_kind="middleware_pipeline",
            evidences=evidences,
            primary_location=fn.location,
            related_locations=[],
            summary=f"Chain of Responsibility: pipeline '{fn.name}' chains {len(middleware_calls)} middleware processing stages",
            base_score=0.20,
        )

    def _build_pipeline_evidences(
        self, fn: Any, middleware_calls: list[str], has_comp: bool, has_threading: bool
    ) -> list[Evidence]:
        evidences = []
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
        return evidences

    def _detect_oop_handlers(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for rec in model.all_records():
            det = self._analyze_handler_record(rec)
            if det:
                results.append(det)
        return results

    def _analyze_handler_record(self, rec: Any) -> Detection | None:
        name_lower = rec.name.lower()
        is_handler_named = any(k in name_lower for k in ("handler", "filter", "processor"))
        successor_fields = self._find_successor_fields(rec.fields)
        chain_methods = self._find_chain_methods(rec.methods)

        if not self._is_handler_candidate(is_handler_named, len(successor_fields) > 0, len(chain_methods) > 0):
            return None

        evidences = self._build_handler_evidences(rec, is_handler_named, successor_fields, chain_methods)
        return self.create_detection(
            target_name=rec.name,
            target_kind="chain_handler_class",
            evidences=evidences,
            primary_location=rec.location,
            summary=f"Chain of Responsibility: class '{rec.name}' processes requests and/or delegates to successor handler",
            base_score=0.30,
        )

    def _is_handler_candidate(self, is_named: bool, has_successor: bool, has_methods: bool) -> bool:
        return (is_named and (has_successor or has_methods)) or (has_successor and has_methods)

    def _find_successor_fields(self, fields: list[str]) -> list[str]:
        keywords = ("successor", "next", "handler", "parent", "chain")
        results = []
        for f in fields:
            f_lower = f.lower()
            if any(k in f_lower for k in keywords):
                results.append(f)
        return results

    def _find_chain_methods(self, methods: list[Any]) -> list[str]:
        keywords = ("setsuccessor", "setnext", "handle", "handlerequest", "process")
        results = []
        for m in methods:
            m_lower = m.name.lower()
            if any(k in m_lower for k in keywords):
                results.append(m.name)
        return results

    def _build_handler_evidences(
        self, rec: Any, is_named: bool, successor_fields: list[str], chain_methods: list[str]
    ) -> list[Evidence]:
        evidences = []
        if is_named:
            evidences.append(
                self.evidence(
                    description=f"Class '{rec.name}' follows Chain of Responsibility handler naming convention",
                    weight=0.45,
                    location=rec.location,
                    code_suffix="HANDLER_CLASS_NAMING",
                )
            )
        if successor_fields:
            evidences.append(
                self.evidence(
                    description=f"Maintains successor/next link to chain handler: {', '.join(successor_fields)}",
                    weight=0.45,
                    location=rec.location,
                    code_suffix="HANDLER_SUCCESSOR_FIELD",
                )
            )
        if chain_methods:
            evidences.append(
                self.evidence(
                    description=f"Declares request processing / successor configuration methods: {', '.join(chain_methods)}",
                    weight=0.40,
                    location=rec.location,
                    code_suffix="HANDLER_CHAIN_METHODS",
                )
            )
        return evidences
