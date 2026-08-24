"""State / Finite State Machine Pattern Detection Rule."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import PatternType, SourceLocation


class StatePatternRule(BasePatternRule):
    """Detects State / Finite State Machine (FSM) pattern instances in Clojure.

    Indicators:
    - State transition functions or multimethods named `transition`, `step`, `next-state`, `handle-state`.
    - Multimethods dispatching on composite `[current-state event]` or state keyword.
    - Explicit state machines managing behavior transitions.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.STATE

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        detections.extend(self._detect_multimethod_states(model))
        detections.extend(self._detect_transition_functions(model))
        detections.extend(self._detect_oop_states(model))
        return detections

    def _detect_multimethod_states(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for ns in model.namespaces.values():
            for mm_name, methods in ns.multimethods.items():
                det = self._analyze_multimethod_state(mm_name, methods)
                if det:
                    results.append(det)
        return results

    def _analyze_multimethod_state(self, mm_name: str, methods: list[Any]) -> Detection | None:
        name_lower = mm_name.lower()
        is_state_named = any(
            k in name_lower for k in ("transition", "fsm", "state-machine", "next-state", "step-state")
        )
        if not (is_state_named or (methods and methods[0].dispatch_fn and "state" in methods[0].dispatch_fn.lower())):
            return None

        primary_fn = methods[0]
        evidences = [
            self.evidence(
                description=f"State transition multimethod '{mm_name}' defines behavioral state machine transitions",
                weight=0.55,
                location=primary_fn.location,
                code_suffix="FSM_TRANSITION_MULTIMETHOD",
            )
        ]
        related_locs: list[SourceLocation] = []
        branches = [m.dispatch_val for m in methods if m.dispatch_val]
        if len(branches) >= 2:
            evidences.append(
                self.evidence(
                    description=f"Defines {len(branches)} discrete state transition branches: {', '.join(branches[:5])}",
                    weight=min(0.50, 0.25 + 0.08 * len(branches)),
                    location=primary_fn.location,
                    code_suffix="STATE_BRANCHES",
                )
            )
            related_locs.extend(m.location for m in methods)

        return self.create_detection(
            target_name=mm_name,
            target_kind="state_machine_multimethod",
            evidences=evidences,
            primary_location=primary_fn.location,
            related_locations=related_locs,
            summary=f"State / FSM pattern: multimethod '{mm_name}' implements state transition logic with {len(branches)} branches",
            base_score=0.25,
        )

    def _detect_transition_functions(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for fn in model.all_functions():
            if not fn.is_multimethod and not fn.parent_multimethod:
                det = self._analyze_transition_fn(fn)
                if det:
                    results.append(det)
        return results

    def _analyze_transition_fn(self, fn: Any) -> Detection | None:
        name_lower = fn.name.lower()
        if name_lower not in ("transition", "next-state", "step-state", "process-state-transition"):
            return None

        params = [p.lower() for plist in fn.parameter_lists for p in plist]
        has_state_params = any("state" in p for p in params) and any(
            "event" in p or "action" in p or "msg" in p for p in params
        )
        if not has_state_params:
            return None

        evidences = [
            self.evidence(
                description=f"Function '{fn.name}' models pure state transition with signature ({', '.join(params)})",
                weight=0.60,
                location=fn.location,
                code_suffix="PURE_STATE_TRANSITION_FN",
            ),
        ]
        return self.create_detection(
            target_name=fn.name,
            target_kind="state_transition_fn",
            evidences=evidences,
            primary_location=fn.location,
            related_locations=[],
            summary=f"State pattern: pure state transition function '{fn.name}' alters behavior based on state changes",
            base_score=0.25,
        )

    def _detect_oop_states(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for proto in model.all_protocols():
            det = self._analyze_state_protocol(proto, model)
            if det:
                results.append(det)
        return results

    def _analyze_state_protocol(self, proto: Any, model: CodeModel) -> Detection | None:
        name_lower = proto.name.lower()
        if not ("state" in name_lower and "strategy" not in name_lower):
            return None

        rec_impls = model.find_records_implementing(proto.name)
        if not (rec_impls or len(proto.methods) >= 1):
            return None

        evidences = [
            self.evidence(
                description=f"Protocol '{proto.name}' defines behavioral State interface: {', '.join(m.name for m in proto.methods)}",
                weight=0.55,
                location=proto.location,
                code_suffix="STATE_INTERFACE_PROTOCOL",
            )
        ]
        for rec in rec_impls:
            evidences.append(
                self.evidence(
                    description=f"Concrete state class '{rec.name}' encapsulates state-specific behavior",
                    weight=0.35,
                    location=rec.location,
                    code_suffix="CONCRETE_STATE_IMPL",
                )
            )

        return self.create_detection(
            target_name=proto.name,
            target_kind="state_protocol",
            evidences=evidences,
            primary_location=proto.location,
            related_locations=[r.location for r in rec_impls],
            summary=f"State pattern: protocol '{proto.name}' allows an object to alter its behavior when internal state changes",
            base_score=0.30,
        )
