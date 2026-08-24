"""Interpreter Pattern Detection Rule."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel, ProtocolModel, RecordModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternType, SourceLocation


class InterpreterPatternRule(BasePatternRule):
    """Detects Interpreter / Domain Expression Evaluator pattern instances in Clojure.

    Indicators:
    - Multimethods or recursive functions named `eval-expr`, `evaluate`, `interpret`, `eval-ast`, `exec-rule`.
    - Functions taking an environment / context map and an expression / AST node to interpret.
    - Polymorphic evaluation of grammar language sentences and domain rules.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.INTERPRETER

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        detections.extend(self._detect_multimethod_interpreters(model))
        detections.extend(self._detect_recursive_evaluators(model))
        detections.extend(self._detect_oop_expressions(model))
        return detections

    def _detect_multimethod_interpreters(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for ns in model.namespaces.values():
            for mm_name, methods in ns.multimethods.items():
                det = self._analyze_multimethod_interp(mm_name, methods, ns)
                if det:
                    results.append(det)
        return results

    def _analyze_multimethod_interp(self, mm_name: str, methods: list[Any], ns: Any) -> Detection | None:
        if not self._is_interpreter_name(mm_name):
            return None

        primary_fn = methods[0] if methods else None
        loc = primary_fn.location if primary_fn else SourceLocation(file_path=ns.file_path, line=1)

        evidences = [
            self.evidence(
                description=f"Interpreter multimethod '{mm_name}' evaluates domain grammar expressions",
                weight=0.60,
                location=loc,
                code_suffix="INTERPRETER_MULTIMETHOD",
            )
        ]
        branches, branch_ev, related_locs = self._extract_interp_branches(methods, loc)
        if branch_ev:
            evidences.append(branch_ev)

        return self.create_detection(
            target_name=mm_name,
            target_kind="expression_interpreter",
            evidences=evidences,
            primary_location=loc,
            related_locations=related_locs,
            summary=f"Interpreter pattern: multimethod '{mm_name}' evaluates domain grammar sentences with {len(branches)} expression rules",
            base_score=0.30,
        )

    def _is_interpreter_name(self, mm_name: str) -> bool:
        name_lower = mm_name.lower()
        return any(k in name_lower for k in ("eval", "interpret", "evaluate", "exec-expr", "eval-ast"))

    def _extract_interp_branches(
        self, methods: list[Any], loc: SourceLocation
    ) -> tuple[list[Any], Evidence | None, list[SourceLocation]]:
        branches = [m.dispatch_val for m in methods if m.dispatch_val]
        if len(branches) < 2:
            return branches, None, []

        ev = self.evidence(
            description=f"Defines evaluation rules for {len(branches)} grammar expression terms: {', '.join(branches[:5])}",
            weight=min(0.50, 0.25 + 0.08 * len(branches)),
            location=loc,
            code_suffix="GRAMMAR_TERMS",
        )
        related_locs = [m.location for m in methods]
        return branches, ev, related_locs

    def _detect_recursive_evaluators(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for fn in model.all_functions():
            if not fn.is_multimethod and not fn.parent_multimethod:
                det = self._analyze_eval_fn(fn)
                if det:
                    results.append(det)
        return results

    def _analyze_eval_fn(self, fn: Any) -> Detection | None:
        name_lower = fn.name.lower()
        if name_lower not in ("eval-expr", "evaluate-expression", "interpret-ast", "eval-rule", "evaluate-rule"):
            return None

        params = [p.lower() for plist in fn.parameter_lists for p in plist]
        has_env_or_expr = any("expr" in p or "ast" in p or "env" in p or "ctx" in p for p in params)
        if not has_env_or_expr:
            return None

        evidences = [
            self.evidence(
                description=f"Function '{fn.name}' acts as recursive sentence interpreter over domain expressions",
                weight=0.65,
                location=fn.location,
                code_suffix="RECURSIVE_EVAL_FN",
            ),
        ]
        return self.create_detection(
            target_name=fn.name,
            target_kind="recursive_interpreter_fn",
            evidences=evidences,
            primary_location=fn.location,
            related_locations=[],
            summary=f"Interpreter pattern: '{fn.name}' recursively evaluates domain grammar expressions in given context",
            base_score=0.30,
        )

    def _detect_oop_expressions(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        candidates: list[ProtocolModel | RecordModel] = list(model.all_protocols())
        for rec in model.all_records():
            if "expression" in rec.name.lower() or any("interpret" in m.name.lower() for m in rec.methods):
                candidates.append(rec)

        seen_targets: set[str] = set()
        for cand in candidates:
            if cand.name not in seen_targets:
                det = self._analyze_expression_candidate(cand, model, seen_targets)
                if det:
                    results.append(det)
        return results

    def _analyze_expression_candidate(self, cand: Any, model: CodeModel, seen_targets: set[str]) -> Detection | None:
        name_lower = cand.name.lower()
        if not ("expression" in name_lower or any("interpret" in m.name.lower() for m in cand.methods)):
            return None

        rec_impls = model.find_records_implementing(cand.name)
        if not (rec_impls or "abstract" in name_lower):
            return None

        seen_targets.add(cand.name)
        evidences = [
            self.evidence(
                description=f"Class/Protocol '{cand.name}' defines domain expression interpretation interface: {', '.join(m.name for m in cand.methods)}",
                weight=0.55,
                location=cand.location,
                code_suffix="EXPRESSION_PROTOCOL",
            )
        ]
        for rec in rec_impls:
            evidences.append(
                self.evidence(
                    description=f"Concrete grammar expression '{rec.name}' evaluates terminal/non-terminal syntax nodes",
                    weight=0.35,
                    location=rec.location,
                    code_suffix="CONCRETE_EXPRESSION_IMPL",
                )
            )
        return self.create_detection(
            target_name=cand.name,
            target_kind="expression_protocol",
            evidences=evidences,
            primary_location=cand.location,
            related_locations=[r.location for r in rec_impls],
            summary=f"Interpreter pattern: class '{cand.name}' defines abstract syntax tree node representation",
            base_score=0.30,
        )
