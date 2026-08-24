"""Observer Pattern Detection Rule."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternType, SourceLocation


class ObserverPatternRule(BasePatternRule):
    """Detects Observer Pattern instances in Clojure.

    Indicators:
    - Calls to `add-watch` attaching a watcher function to an atom/ref/agent/var.
    - Presence of watcher functions accepting standard observer arity: `[key ref old-state new-state]`.
    - Stateful containers (atoms/refs) being observed.
    - Paired `remove-watch` or lifecycle management.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.OBSERVER

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        detections.extend(self._detect_watched_states(model))
        recorded_targets = {d.target_name for d in detections}
        detections.extend(self._detect_standalone_watches(model, recorded_targets))
        recorded_targets = {d.target_name for d in detections}
        detections.extend(self._detect_observer_callbacks(model, recorded_targets))
        detections.extend(self._detect_observer_protocols(model))
        detections.extend(self._detect_subject_classes(model))
        return detections

    def _detect_watched_states(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for state in model.all_states():
            state_watches = [
                w for w in model.all_watches() if w.target_state_name in (state.name, state.qualified_name)
            ]
            if state_watches:
                det = self._create_state_watch_detection(state, state_watches, model)
                results.append(det)
        return results

    def _create_state_watch_detection(self, state: Any, state_watches: list[Any], model: CodeModel) -> Detection:
        evidences = [
            self.evidence(
                description=f"State container '{state.name}' of kind '{state.kind}' is subscribed to via add-watch",
                weight=0.50,
                location=state.location,
                code_suffix="WATCHED_STATE",
            )
        ]
        related_locs: list[SourceLocation] = []
        for w in state_watches:
            evidences.append(
                self.evidence(
                    description=f"Watcher key '{w.watch_key}' registers callback '{w.callback_fn_name}'",
                    weight=0.35,
                    location=w.location,
                    code_suffix="ADD_WATCH_CALL",
                )
            )
            related_locs.append(w.location)
            self._check_watch_fn_signature(w.callback_fn_name, model, evidences, related_locs)

        return self.create_detection(
            target_name=state.name,
            target_kind="state_atom",
            evidences=evidences,
            primary_location=state.location,
            related_locations=related_locs,
            summary=f"Observer pattern: state '{state.name}' has {len(state_watches)} active watcher subscriptions",
        )

    def _check_watch_fn_signature(
        self, callback_name: str, model: CodeModel, evidences: list[Evidence], related_locs: list[SourceLocation]
    ) -> None:
        for fn in model.all_functions():
            if (fn.name == callback_name or fn.qualified_name == callback_name) and any(
                len(p) == 4 for p in fn.parameter_lists
            ):
                evidences.append(
                    self.evidence(
                        description=f"Callback function '{fn.name}' implements 4-parameter observer signature [key ref old-state new-state]",
                        weight=0.25,
                        location=fn.location,
                        code_suffix="OBSERVER_CALLBACK_SIGNATURE",
                    )
                )
                related_locs.append(fn.location)

    def _detect_standalone_watches(self, model: CodeModel, recorded_targets: set[str]) -> list[Detection]:
        results: list[Detection] = []
        for watch in model.all_watches():
            if watch.target_state_name in recorded_targets:
                continue
            evidences = [
                self.evidence(
                    description=f"Explicit add-watch invocation attaching watcher '{watch.watch_key}' to '{watch.target_state_name}'",
                    weight=0.60,
                    location=watch.location,
                    code_suffix="ADD_WATCH_EXPLICIT",
                )
            ]
            results.append(
                self.create_detection(
                    target_name=watch.target_state_name,
                    target_kind="watch_subscription",
                    evidences=evidences,
                    primary_location=watch.location,
                    summary=f"Observer pattern: watcher '{watch.watch_key}' attached to '{watch.target_state_name}'",
                )
            )
        return results

    def _detect_observer_callbacks(self, model: CodeModel, recorded_targets: set[str]) -> list[Detection]:
        results: list[Detection] = []
        for fn in model.all_functions():
            if fn.name not in recorded_targets and any(
                len(p) == 4
                and any(
                    "old" in k.lower() or "state" in k.lower() or "ref" in k.lower() or "key" in k.lower() for k in p
                )
                for p in fn.parameter_lists
            ):
                evidences = [
                    self.evidence(
                        description=f"Function '{fn.name}' matches standard observer callback parameters [key ref old-state new-state]",
                        weight=0.45,
                        location=fn.location,
                        code_suffix="OBSERVER_FN_SIGNATURE",
                    )
                ]
                results.append(
                    self.create_detection(
                        target_name=fn.name,
                        target_kind="observer_callback",
                        evidences=evidences,
                        primary_location=fn.location,
                        summary=f"Observer callback function '{fn.name}' with [key ref old new] signature",
                    )
                )
        return results

    def _detect_observer_protocols(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for proto in model.all_protocols():
            if any(k in proto.name.lower() for k in ("observer", "listener", "subscriber")):
                rec_impls = model.find_records_implementing(proto.name)
                evidences = [
                    self.evidence(
                        description=f"Protocol '{proto.name}' defines Observer interface with callback methods: {', '.join(m.name for m in proto.methods)}",
                        weight=0.55,
                        location=proto.location,
                        code_suffix="OBSERVER_INTERFACE",
                    )
                ]
                for r in rec_impls:
                    evidences.append(
                        self.evidence(
                            description=f"Concrete observer '{r.name}' implements observer interface for '{proto.name}'",
                            weight=0.30,
                            location=r.location,
                            code_suffix="CONCRETE_OBSERVER",
                        )
                    )
                results.append(
                    self.create_detection(
                        target_name=proto.name,
                        target_kind="observer_protocol",
                        evidences=evidences,
                        primary_location=proto.location,
                        related_locations=[r.location for r in rec_impls],
                        summary=f"Observer pattern: observer interface '{proto.name}' implemented by {len(rec_impls)} observer records",
                        base_score=0.30,
                    )
                )
        return results

    def _detect_subject_classes(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for rec in model.all_records():
            det = self._analyze_subject_record(rec)
            if det:
                results.append(det)
        return results

    def _analyze_subject_record(self, rec: Any) -> Detection | None:
        obs_fields = [f for f in rec.fields if self._is_obs_collection(f)]
        obs_m_names = self._get_subject_method_names(rec)

        if not self._is_subject_candidate(rec.name, len(obs_fields) > 0, len(obs_m_names) > 0):
            return None

        evidences = self._build_subject_evidences(rec, obs_fields, obs_m_names)
        return self.create_detection(
            target_name=rec.name,
            target_kind="subject_class",
            evidences=evidences,
            primary_location=rec.location,
            summary=f"Observer pattern: class '{rec.name}' manages and notifies observers of state changes",
            base_score=0.30,
        )

    def _is_subject_candidate(self, name: str, has_obs_field: bool, has_obs_methods: bool) -> bool:
        name_lower = name.lower()
        is_named = "subject" in name_lower or "observable" in name_lower
        return has_obs_field or (has_obs_methods and is_named)

    def _get_subject_method_names(self, rec: Any) -> list[str]:
        prefixes = ("attach", "detach", "register", "unregister", "subscribe", "notify")
        results = []
        for m in rec.methods:
            s_name = m.name.split(".")[-1].lower()
            if s_name.startswith(prefixes):
                results.append(m.name.split(".")[-1])
        return results

    def _build_subject_evidences(self, rec: Any, obs_fields: list[str], obs_m_names: list[str]) -> list[Evidence]:
        evidences = []
        name_lower = rec.name.lower()
        if "subject" in name_lower or "observable" in name_lower:
            evidences.append(
                self.evidence(
                    description=f"Class '{rec.name}' represents Observable Subject managing event subscribers",
                    weight=0.45,
                    location=rec.location,
                    code_suffix="SUBJECT_CLASS_NAMING",
                )
            )
        if obs_fields:
            evidences.append(
                self.evidence(
                    description=f"Maintains list/collection of observers: {', '.join(obs_fields)}",
                    weight=0.40,
                    location=rec.location,
                    code_suffix="OBSERVER_COLLECTION_FIELD",
                )
            )
        if obs_m_names:
            evidences.append(
                self.evidence(
                    description=f"Declares observer lifecycle/notification methods: {', '.join(obs_m_names)}",
                    weight=0.40,
                    location=rec.location,
                    code_suffix="OBSERVER_MANAGEMENT_METHODS",
                )
            )
        return evidences

    def _is_obs_collection(self, field_name: str) -> bool:
        f = field_name.lower()
        if any(
            f.endswith(suffix)
            for suffix in ("_state", "_id", "_name", "_count", "_type", "_ptr", "_val", "_flag", "_status")
        ):
            return False
        return any(
            k in f
            for k in ("observers", "listeners", "subscribers", "views", "watchers", "observer_list", "listener_list")
        )
