"""Template Method / Resource Bracket Pattern Rule."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternType


class TemplateMethodRule(BasePatternRule):
    """Detects Template Method / Functional Resource Bracket pattern instances.

    Indicators:
    - Macros or functions named with the `with-*` bracket convention (e.g. with-open, with-connection, with-lock).
    - Functions encapsulating invariant try/finally, acquire/release, or setup/teardown logic around a caller-supplied body/function.
    - Functions taking before/after hooks or wrapping lambda execution.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.TEMPLATE_METHOD

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        detections.extend(self._detect_functional_brackets(model))
        detections.extend(self._detect_oop_template_methods(model))
        return detections

    def _detect_functional_brackets(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for fn in model.all_functions():
            if not fn.is_multimethod and not fn.parent_multimethod:
                det = self._analyze_functional_bracket(fn)
                if det:
                    results.append(det)
        return results

    def _analyze_functional_bracket(self, fn: Any) -> Detection | None:
        is_with_naming = fn.name.lower().startswith(("with-", "with_"))
        has_try_finally = "try" in fn.body_text and ("finally" in fn.body_text or "catch" in fn.body_text)
        has_hook_param = self._has_bracket_hook_param(fn)

        if not self._is_bracket_candidate(is_with_naming, fn.is_macro, has_try_finally, has_hook_param):
            return None

        evidences = self._build_functional_bracket_evidences(fn, is_with_naming, has_try_finally, has_hook_param)
        return self.create_detection(
            target_name=fn.name,
            target_kind="template_bracket",
            evidences=evidences,
            primary_location=fn.location,
            related_locations=[],
            summary=f"Template Method: '{fn.name}' encapsulates invariant algorithm/resource skeleton with customizable execution body",
            base_score=0.20,
        )

    def _is_bracket_candidate(self, is_with: bool, is_macro: bool, has_try: bool, has_hook: bool) -> bool:
        return (is_with and (is_macro or has_try or has_hook)) or (has_try and has_hook)

    def _has_bracket_hook_param(self, fn: Any) -> bool:
        hook_names = ("f", "callback", "handler", "body", "action", "task")
        for plist in fn.parameter_lists:
            for p in plist:
                if p.lower() in hook_names:
                    return True
        return False

    def _build_functional_bracket_evidences(
        self, fn: Any, is_with_naming: bool, has_try_finally: bool, has_hook_param: bool
    ) -> list[Evidence]:
        evidences: list[Evidence] = []
        if is_with_naming:
            evidences.append(
                self.evidence(
                    description=f"Follows idiomatic Clojure 'with-*' resource bracket template naming: '{fn.name}'",
                    weight=0.50,
                    location=fn.location,
                    code_suffix="WITH_BRACKET_NAMING",
                )
            )
        if fn.is_macro and is_with_naming:
            evidences.append(
                self.evidence(
                    description="Macro encapsulates algorithmic skeleton expanding user-supplied body expressions",
                    weight=0.40,
                    location=fn.location,
                    code_suffix="MACRO_BRACKET",
                )
            )
        if has_try_finally:
            evidences.append(
                self.evidence(
                    description="Encapsulates invariant resource safety skeleton (try/finally or try/catch)",
                    weight=0.45,
                    location=fn.location,
                    code_suffix="TRY_FINALLY_BRACKET",
                )
            )
        if has_hook_param:
            evidences.append(
                self.evidence(
                    description="Accepts customizable callback parameter executed inside template skeleton",
                    weight=0.35,
                    location=fn.location,
                    code_suffix="CALLBACK_PARAMETER",
                )
            )
        return evidences

    def _detect_oop_template_methods(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for proto in model.all_protocols():
            det = self._analyze_template_protocol(proto, model)
            if det:
                results.append(det)
        return results

    def _analyze_template_protocol(self, proto: Any, model: CodeModel) -> Detection | None:
        primitive_methods = self._get_primitive_methods(proto)
        has_template_method = self._has_template_method(proto)

        if not primitive_methods and not (has_template_method and len(proto.methods) >= 2):
            return None

        rec_impls = model.find_records_implementing(proto.name)
        evidences = self._build_template_proto_evidences(proto, primitive_methods, rec_impls)

        return self.create_detection(
            target_name=proto.name,
            target_kind="template_method_protocol",
            evidences=evidences,
            primary_location=proto.location,
            related_locations=[r.location for r in rec_impls],
            summary=f"Template Method pattern: '{proto.name}' defines skeleton of algorithm in base class",
            base_score=0.30,
        )

    def _get_primitive_methods(self, proto: Any) -> list[Any]:
        keywords = ("primitive", "step", "template", "hook", "do_")
        results = []
        for m in proto.methods:
            m_lower = m.name.lower()
            if any(k in m_lower for k in keywords):
                results.append(m)
        return results

    def _has_template_method(self, proto: Any) -> bool:
        for m in proto.methods:
            m_lower = m.name.lower()
            if "template" in m_lower or "execute" in m_lower or "run" in m_lower:
                return True
        return False

    def _build_template_proto_evidences(
        self, proto: Any, primitive_methods: list[Any], rec_impls: list[Any]
    ) -> list[Evidence]:
        active_methods = primitive_methods if primitive_methods else proto.methods
        evidences = [
            self.evidence(
                description=f"Class '{proto.name}' defines template algorithm skeleton with primitive operations: {', '.join(m.name for m in active_methods)}",
                weight=0.55,
                location=proto.location,
                code_suffix="TEMPLATE_METHOD_SKELETON",
            )
        ]
        for rec in rec_impls:
            evidences.append(
                self.evidence(
                    description=f"Subclass '{rec.name}' overrides primitive step operations without changing algorithm structure",
                    weight=0.35,
                    location=rec.location,
                    code_suffix="CONCRETE_TEMPLATE_IMPL",
                )
            )
        return evidences
