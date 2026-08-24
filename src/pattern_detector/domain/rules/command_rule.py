"""Command / CQRS Pattern Detection Rule."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import Evidence, PatternType, SourceLocation


class CommandPatternRule(BasePatternRule):
    """Detects Command / CQRS Message Handler pattern instances.

    Indicators:
    - Multimethods dispatching on command/event message keys (:command, :type, :op, :action, :event).
    - Functions named handle-command, execute-command, dispatch-event, process-command.
    - Protocols defining execute / handle with multiple command record implementations.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.COMMAND

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        detections.extend(self._detect_multimethod_commands(model))
        detections.extend(self._detect_protocol_commands(model))
        return detections

    def _detect_multimethod_commands(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for ns in model.namespaces.values():
            for mm_name, methods in ns.multimethods.items():
                det = self._analyze_multimethod_command(mm_name, methods, ns)
                if det:
                    results.append(det)
        return results

    def _analyze_multimethod_command(self, mm_name: str, methods: list[Any], ns: Any) -> Detection | None:
        is_command_named = self._is_command_name(mm_name)
        evidences, related_locs = self._collect_multimethod_command_evidences(mm_name, methods, is_command_named, ns)

        if not ((is_command_named and len(methods) >= 1) or len(evidences) >= 2):
            return None

        primary_loc = methods[0].location if methods else SourceLocation(file_path=ns.file_path, line=1)
        return self.create_detection(
            target_name=mm_name,
            target_kind="command_handler",
            evidences=evidences,
            primary_location=primary_loc,
            related_locations=related_locs,
            summary=f"Command / CQRS pattern: multimethod '{mm_name}' handles polymorphic command messages",
            base_score=0.25,
        )

    def _is_command_name(self, name: str) -> bool:
        name_lower = name.lower()
        keywords = ("command", "cmd", "event", "action", "msg", "message", "dispatch", "handle-")
        return any(k in name_lower for k in keywords)

    def _collect_multimethod_command_evidences(
        self, mm_name: str, methods: list[Any], is_named: bool, ns: Any
    ) -> tuple[list[Evidence], list[SourceLocation]]:
        evidences: list[Evidence] = []
        related_locs: list[SourceLocation] = []

        if is_named:
            evidences.append(
                self.evidence(
                    description=f"Multimethod '{mm_name}' follows command/event dispatcher naming",
                    weight=0.45,
                    location=methods[0].location if methods else SourceLocation(file_path=ns.file_path, line=1),
                    code_suffix="COMMAND_DISPATCHER_NAMING",
                )
            )

        if methods:
            primary_fn = methods[0]
            dispatch_str = primary_fn.dispatch_fn or ""
            if any(k in dispatch_str for k in (":type", ":command", ":cmd", ":action", ":op", ":event")):
                evidences.append(
                    self.evidence(
                        description=f"Dispatches command execution based on message discriminant key '{dispatch_str}'",
                        weight=0.55,
                        location=primary_fn.location,
                        code_suffix="COMMAND_DISCRIMINANT_KEY",
                    )
                )

            branches = [m.dispatch_val for m in methods if m.dispatch_val]
            if len(branches) >= 2:
                evidences.append(
                    self.evidence(
                        description=f"Implements {len(branches)} distinct command handler branches: {', '.join(branches[:5])}",
                        weight=min(0.50, 0.25 + 0.08 * len(branches)),
                        location=primary_fn.location,
                        code_suffix="COMMAND_BRANCHES",
                    )
                )
                related_locs.extend(m.location for m in methods)

        return evidences, related_locs

    def _detect_protocol_commands(self, model: CodeModel) -> list[Detection]:
        results: list[Detection] = []
        for proto in model.all_protocols():
            det = self._analyze_command_protocol(proto, model)
            if det:
                results.append(det)
        return results

    def _analyze_command_protocol(self, proto: Any, model: CodeModel) -> Detection | None:
        if not self._is_command_proto(proto):
            return None

        rec_impls = model.find_records_implementing(proto.name)
        if not rec_impls:
            return None

        evidences = [
            self.evidence(
                description=f"Protocol '{proto.name}' defines Command interface with methods: {', '.join(m.name for m in proto.methods)}",
                weight=0.50,
                location=proto.location,
                code_suffix="COMMAND_PROTOCOL",
            ),
        ]
        for rec in rec_impls:
            evidences.append(
                self.evidence(
                    description=f"Record '{rec.name}' encapsulates executable command parameters and behavior",
                    weight=0.30,
                    location=rec.location,
                    code_suffix="COMMAND_RECORD",
                )
            )

        return self.create_detection(
            target_name=proto.name,
            target_kind="command_protocol",
            evidences=evidences,
            primary_location=proto.location,
            related_locations=[r.location for r in rec_impls],
            summary=f"Command pattern: protocol '{proto.name}' implemented by {len(rec_impls)} command records",
            base_score=0.30,
        )

    def _is_command_proto(self, proto: Any) -> bool:
        name_lower = proto.name.lower()
        if any(k in name_lower for k in ("command", "cmd", "action", "executable", "task", "job")):
            return True
        cmd_methods = ("execute", "exec", "undo", "redo")
        for m in proto.methods:
            if m.name.lower() in cmd_methods:
                return True
        return False
