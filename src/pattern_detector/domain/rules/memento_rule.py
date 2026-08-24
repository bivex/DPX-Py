"""Memento Pattern Detection Rule."""

from __future__ import annotations

from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.detection import Detection
from pattern_detector.domain.rules.base import BasePatternRule
from pattern_detector.domain.value_objects import PatternType


class MementoPatternRule(BasePatternRule):
    """Detects Memento / State Snapshot & History pattern instances in Clojure.

    Indicators:
    - Functions named `save-snapshot`, `restore-snapshot`, `create-memento`, `restore-memento`, `checkpoint`, `undo`, `redo`.
    - History atoms or records tracking historical state snapshots.
    - Protocols defining state capture and rollback capabilities.
    """

    @property
    def pattern_type(self) -> PatternType:
        return PatternType.MEMENTO

    def detect(self, model: CodeModel) -> list[Detection]:
        detections: list[Detection] = []
        for ns in model.namespaces.values():
            memento_fns = self._find_memento_functions(ns)
            if self._is_memento_group(memento_fns):
                detections.append(self._build_memento_detection(ns, memento_fns))
        return detections

    def _find_memento_functions(self, ns: Any) -> list[Any]:
        keywords = ("snapshot", "memento", "checkpoint", "undo", "redo", "save_state", "restore_state")
        results = []
        for fn in ns.functions.values():
            if "Rule" not in fn.name and "Test" not in fn.name:
                local_name = fn.name.split(".")[-1].lower()
                if any(k in local_name for k in keywords):
                    results.append(fn)
        return results

    def _is_memento_group(self, fns: list[Any]) -> bool:
        if len(fns) >= 2:
            return True
        for f in fns:
            local_name = f.name.split(".")[-1].lower()
            if "memento" in local_name or "snapshot" in local_name:
                return True
        return False

    def _build_memento_detection(self, ns: Any, memento_fns: list[Any]) -> Detection:
        evidences = [
            self.evidence(
                description=f"Namespace '{ns.name}' defines {len(memento_fns)} state snapshot/restore functions: {', '.join(f.name for f in memento_fns)}",
                weight=min(0.65, 0.40 + 0.10 * len(memento_fns)),
                location=memento_fns[0].location,
                code_suffix="MEMENTO_SNAPSHOT_FNS",
            )
        ]
        related_locs = [f.location for f in memento_fns]
        return self.create_detection(
            target_name=memento_fns[0].name,
            target_kind="memento_history_manager",
            evidences=evidences,
            primary_location=memento_fns[0].location,
            related_locations=related_locs,
            summary=f"Memento pattern: snapshot & history management in namespace '{ns.name}' ({len(memento_fns)} functions)",
            base_score=0.30,
        )
