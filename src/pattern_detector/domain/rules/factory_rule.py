"""Factory Method / Constructor Helpers Pattern Detection Rule."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternType, SourceLocation


class FactoryPatternRule(BasePatternRule):
    """Detects Factory Method / Builder / Constructor Helper instances in Clojure.

    Indicators:
    - Dedicated factory functions with prefixes `make-*`, `create-*`, `new-*`, `build-*`.
    - Functions encapsulating construction of records via `->Record` or `map->Record`.
    - Factory functions performing polymorphic object creation based on config parameters.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.FACTORY_METHOD

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        all_record_names = {r.name for r in model.all_records()}
        all_record_constructors = {f"->{r.name}" for r in model.all_records()} | {
            f"map->{r.name}" for r in model.all_records()
        }

        detections.extend(self._detect_factory_functions(model, all_record_names, all_record_constructors))
        detections.extend(self._detect_factory_method_protocols(model))
        return detections

    def _detect_factory_functions(
        self, model: CodeModel, all_record_names: set[str], all_record_constructors: set[str]
    ) -> list[Detection]:
        results: list[Detection] = []
        for fn in model.all_functions():
            if not fn.is_multimethod and not fn.parent_multimethod:
                det = self._analyze_factory_function(fn, all_record_names, all_record_constructors, model)
                if det:
                    results.append(det)
        return results

    def _analyze_factory_function(
        self, fn: Any, all_record_names: set[str], all_record_constructors: set[str], model: CodeModel
    ) -> Detection | None:
        evidences: list[Evidence] = []
        related_locs: list[SourceLocation] = []
        name_lower = fn.name.lower()
        is_factory_name = name_lower.startswith(
            ("make-", "make_", "create-", "create_", "new-", "build-", "construct-")
        )

        if is_factory_name:
            evidences.append(
                self.evidence(
                    description=f"Follows factory function naming convention '{fn.name}'",
                    weight=0.35,
                    location=fn.location,
                    code_suffix="FACTORY_NAMING",
                )
            )

        instantiated_records = [
            rec
            for rec in all_record_names
            if f"->{rec}" in fn.calls or f"map->{rec}" in fn.calls or rec in fn.instantiates_types
        ]
        inst_evs, inst_locs = self._collect_instantiation_evidences(
            fn, instantiated_records, all_record_constructors, model
        )
        evidences.extend(inst_evs)
        related_locs.extend(inst_locs)

        has_record_ctor = any(call in all_record_constructors or call.startswith(("->", "map->")) for call in fn.calls)
        if not (evidences and (len(evidences) >= 2 or (is_factory_name and (instantiated_records or has_record_ctor)))):
            return None

        return self.create_detection(
            target_name=fn.name,
            target_kind="factory_function",
            evidences=evidences,
            primary_location=fn.location,
            related_locations=related_locs,
            summary=f"Factory pattern: constructor helper function '{fn.name}' creating structured domain objects",
            base_score=0.15,
        )

    def _collect_instantiation_evidences(
        self,
        fn: Any,
        instantiated: list[str],
        all_ctors: set[str],
        model: CodeModel,
    ) -> tuple[list[Evidence], list[SourceLocation]]:
        evidences: list[Evidence] = []
        related_locs: list[SourceLocation] = []
        if instantiated:
            evidences.append(
                self.evidence(
                    description=f"Encapsulates instantiation of record(s): {', '.join(instantiated)}",
                    weight=0.45,
                    location=fn.location,
                    code_suffix="RECORD_INSTANTIATION",
                )
            )
            for rec_name in instantiated:
                rec = model.find_record(rec_name) if hasattr(model, "find_record") else None
                if rec:
                    related_locs.append(rec.location)
        elif any(call in all_ctors or call.startswith(("->", "map->")) for call in fn.calls):
            evidences.append(
                self.evidence(
                    description="Invokes record constructor (->Type or map->Type) with default parameters/validation",
                    weight=0.40,
                    location=fn.location,
                    code_suffix="CTOR_INVOCATION",
                )
            )
        return evidences, related_locs

    def _detect_factory_method_protocols(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for proto in model.all_protocols():
            det = self._analyze_factory_proto(proto, model)
            if det:
                results.append(det)
        return results

    def _analyze_factory_proto(self, proto: Any, model: CodeModel) -> Detection | None:
        if not self._is_factory_proto_name(proto.name):
            return None

        creation_methods = self._get_creation_methods(proto)
        rec_impls = model.find_records_implementing(proto.name)
        if not creation_methods and not rec_impls:
            return None

        evidences = self._build_factory_proto_evidences(proto, creation_methods, rec_impls)
        return self.create_detection(
            target_name=proto.name,
            target_kind="factory_method_protocol",
            evidences=evidences,
            primary_location=proto.location,
            related_locations=[r.location for r in rec_impls],
            summary=f"Factory Method pattern: '{proto.name}' declares factory creation contract implemented by {len(rec_impls)} concrete creator(s)",
            base_score=0.30,
        )

    def _is_factory_proto_name(self, name: str) -> bool:
        name_lower = name.lower()
        if "builder" in name_lower:
            return False
        return any(k in name_lower for k in ("creator", "factory", "provider"))

    def _get_creation_methods(self, proto: Any) -> list[Any]:
        results = []
        prefixes = ("create", "make", "new")
        for m in proto.methods:
            if m.name.lower().startswith(prefixes):
                results.append(m)
        return results

    def _build_factory_proto_evidences(
        self, proto: Any, creation_methods: list[Any], rec_impls: list[Any]
    ) -> list[Evidence]:
        active_methods = creation_methods if creation_methods else proto.methods
        evidences = [
            self.evidence(
                description=f"Protocol '{proto.name}' defines Factory Method creation contract: {', '.join(m.name for m in active_methods)}",
                weight=0.55,
                location=proto.location,
                code_suffix="FACTORY_METHOD_PROTOCOL",
            )
        ]
        for rec in rec_impls:
            evidences.append(
                self.evidence(
                    description=f"Concrete creator '{rec.name}' overrides factory method(s) to produce specific products",
                    weight=0.35,
                    location=rec.location,
                    code_suffix="CONCRETE_CREATOR_IMPL",
                )
            )
        return evidences
