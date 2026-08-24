"""Builder Pattern Detection Rule."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternType, SourceLocation


class BuilderPatternRule(BasePatternRule):
    """Detects Builder / Fluent Configuration pattern instances in Clojure.

    Indicators:
    - Sets of functions with prefixes like `with-*`, `set-*`, `add-*` that take a builder/config
      map or record as first parameter and return the updated instance (fluent chaining).
    - Functions named `build-*`, `create-builder`, `new-builder`, or records named `*Builder`, `*Config`.
    - Functions assembling complex entities step-by-step through `assoc`/`update`/`merge`.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.BUILDER

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        detections.extend(self._detect_dsl_builders(model))
        detections.extend(self._detect_protocol_builders(model))
        detections.extend(self._detect_class_builders(model))
        return detections

    def _detect_dsl_builders(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for ns in model.namespaces.values():
            det = self._detect_namespace_dsl(ns)
            if det:
                results.append(det)
        return results

    def _detect_namespace_dsl(self, ns: Any) -> Detection | None:
        step_fns, terminal_build_fns = self._classify_builder_functions(ns)
        if len(step_fns) < 2 and not (len(step_fns) >= 1 and len(terminal_build_fns) >= 1):
            return None

        evidences = self._build_dsl_evidences(ns, step_fns, terminal_build_fns)
        related_locs: list[SourceLocation] = [f.location for f in step_fns]
        related_locs.extend(f.location for f in terminal_build_fns)

        target_name = terminal_build_fns[0].name if terminal_build_fns else step_fns[0].name
        primary_loc = step_fns[0].location if step_fns else terminal_build_fns[0].location

        return self.create_detection(
            target_name=target_name,
            target_kind="builder_dsl",
            evidences=evidences,
            primary_location=primary_loc,
            related_locations=related_locs,
            summary=f"Builder pattern: fluent builder DSL in namespace '{ns.name}' with {len(step_fns)} configuration steps",
            base_score=0.30,
        )

    def _classify_builder_functions(self, ns: Any) -> tuple[list[Any], list[Any]]:
        step_fns = []
        terminal_build_fns = []
        for fn in ns.functions.values():
            if fn.is_multimethod or fn.parent_multimethod:
                continue
            name_lower = fn.name.lower()
            if name_lower.startswith(("build-", "build_")) or name_lower in ("build", "finish-build"):
                terminal_build_fns.append(fn)
            elif self._is_step_fn(fn, name_lower):
                step_fns.append(fn)
        return step_fns, terminal_build_fns

    def _is_step_fn(self, fn: Any, name_lower: str) -> bool:
        if not name_lower.startswith(("with-", "set-", "add-", "use-")) or name_lower.startswith(
            ("with-open", "with-lock", "with-transaction")
        ):
            return False
        has_assoc = any(k in fn.body_text for k in ("assoc", "update", "merge", "assoc-in", "update-in"))
        params = [p.lower() for plist in fn.parameter_lists for p in plist]
        has_param = any(
            "builder" in p or "config" in p or "opts" in p or "ctx" in p or p in ("b", "c", "m", "this") for p in params
        )
        return has_assoc or has_param

    def _build_dsl_evidences(self, ns: Any, step_fns: list[Any], terminal_build_fns: list[Any]) -> list[Evidence]:
        evidences: list[Evidence] = [
            self.evidence(
                description=f"Namespace '{ns.name}' defines {len(step_fns)} fluent configuration step functions: {', '.join(f.name for f in step_fns[:5])}",
                weight=min(0.60, 0.30 + 0.10 * len(step_fns)),
                location=step_fns[0].location if step_fns else next(iter(ns.functions.values())).location,
                code_suffix="BUILDER_STEP_FUNCTIONS",
            )
        ]
        if terminal_build_fns:
            evidences.append(
                self.evidence(
                    description=f"Provides terminal build / instantiation function(s): {', '.join(f.name for f in terminal_build_fns)}",
                    weight=0.35,
                    location=terminal_build_fns[0].location,
                    code_suffix="TERMINAL_BUILD_FN",
                )
            )
        return evidences

    def _detect_protocol_builders(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for proto in model.all_protocols():
            if "builder" in proto.name.lower():
                rec_impls = model.find_records_implementing(proto.name)
                evidences = [
                    self.evidence(
                        description=f"Protocol '{proto.name}' defines builder construction interface with methods: {', '.join(m.name for m in proto.methods)}",
                        weight=0.55,
                        location=proto.location,
                        code_suffix="BUILDER_PROTOCOL",
                    )
                ]
                for rec in rec_impls:
                    evidences.append(
                        self.evidence(
                            description=f"Concrete builder '{rec.name}' implements step-by-step assembly for '{proto.name}'",
                            weight=0.35,
                            location=rec.location,
                            code_suffix="CONCRETE_BUILDER_IMPL",
                        )
                    )
                results.append(
                    self.create_detection(
                        target_name=proto.name,
                        target_kind="builder_protocol",
                        evidences=evidences,
                        primary_location=proto.location,
                        related_locations=[r.location for r in rec_impls],
                        summary=f"Builder pattern: protocol '{proto.name}' defines construction steps implemented by {len(rec_impls)} concrete builders",
                        base_score=0.30,
                    )
                )
        return results

    def _detect_class_builders(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for rec in model.all_records():
            if rec.name.endswith("Rule") or rec.name.endswith("Test"):
                continue
            det = self._detect_class_builder(rec)
            if det:
                results.append(det)
        return results

    def _detect_class_builder(self, rec: Any) -> Detection | None:
        name_lower = rec.name.lower()
        step_methods = self._get_step_methods(rec)
        build_fn = self._find_terminal_build_method(rec)
        is_builder_named = "builder" in name_lower

        if not ((is_builder_named and (step_methods or build_fn)) or (len(step_methods) >= 2 and build_fn)):
            return None

        evidences = []
        if is_builder_named:
            evidences.append(
                self.evidence(
                    description=f"Class '{rec.name}' follows Builder naming convention for complex object assembly",
                    weight=0.45,
                    location=rec.location,
                    code_suffix="BUILDER_CLASS_NAMING",
                )
            )
        if step_methods:
            evidences.append(
                self.evidence(
                    description=f"Class '{rec.name}' defines {len(step_methods)} fluent configuration method(s): {', '.join(m.name.split('.')[-1] for m in step_methods[:5])}",
                    weight=0.45,
                    location=step_methods[0].location,
                    code_suffix="BUILDER_STEP_METHODS",
                )
            )
        if build_fn:
            evidences.append(
                self.evidence(
                    description=f"Class '{rec.name}' provides terminal assembly method '{build_fn.name.split('.')[-1]}()'",
                    weight=0.40,
                    location=build_fn.location,
                    code_suffix="BUILDER_TERMINAL_METHOD",
                )
            )
        return self.create_detection(
            target_name=rec.name,
            target_kind="builder_class",
            evidences=evidences,
            primary_location=rec.location,
            related_locations=[m.location for m in step_methods],
            summary=f"Builder pattern: class '{rec.name}' provides fluent step-by-step assembly with {len(step_methods)} steps",
            base_score=0.30,
        )

    def _get_step_methods(self, rec: Any) -> list[Any]:
        return [
            m
            for m in rec.methods
            if (
                m.name.split(".")[-1].lower().startswith(("with_", "set_", "add_", "append_", "use_"))
                or "return self" in m.body_text.lower()
            )
            and m.name.split(".")[-1].lower()
            not in ("__init__", "build", "create", "construct", "get_result", "to_dict", "to_request")
            and not m.name.split(".")[-1].lower().startswith(("with_open", "with_lock"))
        ]

    def _find_terminal_build_method(self, rec: Any) -> Any | None:
        targets = ("build", "create", "construct", "get_result", "to_dict", "to_request")
        return next((m for m in rec.methods if m.name.split(".")[-1].lower() in targets), None)
