"""Observer Pattern Detection Rule."""

from __future__ import annotations

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

        # 1. State-centric detection (states that have watchers attached)
        for state in model.all_states():
            state_watches = [w for w in model.all_watches() if w.target_state_name in (state.name, state.qualified_name)]
            if state_watches:
                evidences: list[Evidence] = []
                related_locs: list[SourceLocation] = []

                evidences.append(
                    self.evidence(
                        description=f"State container '{state.name}' of kind '{state.kind}' is subscribed to via add-watch",
                        weight=0.50,
                        location=state.location,
                        code_suffix="WATCHED_STATE",
                    )
                )

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

                    # Check if the callback function conforms to 4-parameter observer signature
                    for fn in model.all_functions():
                        if fn.name == w.callback_fn_name or fn.qualified_name == w.callback_fn_name:
                            # Standard Clojure watch fn arity: [key ref old-state new-state]
                            has_4_arity = any(len(params) == 4 for params in fn.parameter_lists)
                            if has_4_arity:
                                evidences.append(
                                    self.evidence(
                                        description=f"Callback function '{fn.name}' implements 4-parameter observer signature [key ref old-state new-state]",
                                        weight=0.25,
                                        location=fn.location,
                                        code_suffix="OBSERVER_CALLBACK_SIGNATURE",
                                    )
                                )
                                related_locs.append(fn.location)

                detections.append(
                    self.create_detection(
                        target_name=state.name,
                        target_kind="state_atom",
                        evidences=evidences,
                        primary_location=state.location,
                        related_locations=related_locs,
                        summary=f"Observer pattern: state '{state.name}' has {len(state_watches)} active watcher subscriptions",
                    )
                )

        # 2. Standalone add-watch calls or functions with watch callbacks
        recorded_watch_targets = {d.target_name for d in detections}
        for watch in model.all_watches():
            if watch.target_state_name in recorded_watch_targets:
                continue

            evidences = [
                self.evidence(
                    description=f"Explicit add-watch invocation attaching watcher '{watch.watch_key}' to '{watch.target_state_name}'",
                    weight=0.60,
                    location=watch.location,
                    code_suffix="ADD_WATCH_EXPLICIT",
                )
            ]
            detections.append(
                self.create_detection(
                    target_name=watch.target_state_name,
                    target_kind="watch_subscription",
                    evidences=evidences,
                    primary_location=watch.location,
                    summary=f"Observer pattern: watcher '{watch.watch_key}' attached to '{watch.target_state_name}'",
                )
            )

        # 3. Callback functions with 4-parameter watch signature [k r o n]
        for fn in model.all_functions():
            if any(
                len(params) == 4 and any("old" in p.lower() or "state" in p.lower() or "ref" in p.lower() or "key" in p.lower() for p in params)
                for params in fn.parameter_lists
            ) and fn.name not in [d.target_name for d in detections]:
                evidences = [
                    self.evidence(
                        description=f"Function '{fn.name}' matches standard observer callback parameters [key ref old-state new-state]",
                        weight=0.45,
                        location=fn.location,
                        code_suffix="OBSERVER_FN_SIGNATURE",
                    )
                ]
                detections.append(
                    self.create_detection(
                        target_name=fn.name,
                        target_kind="observer_callback",
                        evidences=evidences,
                        primary_location=fn.location,
                        summary=f"Observer callback function '{fn.name}' with [key ref old new] signature",
                    )
                )

        # 4. OOP Observer / Subject Pattern in C++
        for proto in model.all_protocols():
            name_lower = proto.name.lower()
            if any(k in name_lower for k in ("observer", "listener", "subscriber")):
                evidences = [
                    self.evidence(
                        description=f"Protocol '{proto.name}' defines Observer interface with callback methods: {', '.join(m.name for m in proto.methods)}",
                        weight=0.55,
                        location=proto.location,
                        code_suffix="OBSERVER_INTERFACE",
                    )
                ]
                rec_impls = model.find_records_implementing(proto.name)
                for r in rec_impls:
                    evidences.append(
                        self.evidence(
                            description=f"Concrete observer '{r.name}' implements observer interface for '{proto.name}'",
                            weight=0.30,
                            location=r.location,
                            code_suffix="CONCRETE_OBSERVER",
                        )
                    )
                detections.append(
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

        def is_obs_collection(field_name: str) -> bool:
            f = field_name.lower()
            if any(f.endswith(suffix) for suffix in ("_state", "_id", "_name", "_count", "_type", "_ptr", "_val", "_flag", "_status")):
                return False
            return any(k in f for k in ("observers", "listeners", "subscribers", "views", "watchers", "observer_list", "listener_list"))

        # Subject classes managing observer lists
        for rec in model.all_records():
            name_lower = rec.name.lower()
            obs_fields = [f for f in rec.fields if is_obs_collection(f)]
            has_obs_field = len(obs_fields) > 0
            has_obs_methods = any(
                m.name.lower().startswith(("attach", "detach", "register", "unregister", "subscribe", "notify"))
                for m in rec.methods
            )
            if has_obs_field or (has_obs_methods and "subject" in name_lower):
                evidences = []
                if "subject" in name_lower or "observable" in name_lower:
                    evidences.append(
                        self.evidence(
                            description=f"Class '{rec.name}' represents Observable Subject managing event subscribers",
                            weight=0.45,
                            location=rec.location,
                            code_suffix="SUBJECT_CLASS_NAMING",
                        )
                    )
                if has_obs_field:
                    evidences.append(
                        self.evidence(
                            description=f"Maintains list/collection of observers: {', '.join(obs_fields)}",
                            weight=0.40,
                            location=rec.location,
                            code_suffix="OBSERVER_COLLECTION_FIELD",
                        )
                    )
                if has_obs_methods:
                    evidences.append(
                        self.evidence(
                            description=f"Declares observer lifecycle/notification methods: {', '.join([m.name for m in rec.methods if m.name.lower().startswith(('attach', 'detach', 'register', 'unregister', 'subscribe', 'notify'))])}",
                            weight=0.40,
                            location=rec.location,
                            code_suffix="OBSERVER_MANAGEMENT_METHODS",
                        )
                    )
                if evidences:
                    detections.append(
                        self.create_detection(
                            target_name=rec.name,
                            target_kind="subject_class",
                            evidences=evidences,
                            primary_location=rec.location,
                            summary=f"Observer pattern: subject '{rec.name}' manages event subscriptions and notifications",
                            base_score=0.30,
                        )
                    )

        return detections
