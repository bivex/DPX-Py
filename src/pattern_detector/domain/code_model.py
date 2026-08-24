"""Agnostic Domain Code Model.

Represents structural and semantic constructs (Protocols, Records/Classes,
Functions, State, Invocations, Namespaces, Dependency Graphs) parsed from source code
without direct dependency on any AST framework.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from pattern_detector.domain.value_objects import SourceLocation


@dataclass
class MethodSignature:
    """Represents a method signature inside a protocol/interface."""

    name: str
    parameter_lists: list[list[str]] = field(default_factory=list)
    docstring: str | None = None
    location: SourceLocation | None = None


@dataclass
class NamedCodeEntity:
    """Base class for named code entities with namespace qualification."""

    name: str
    namespace: str

    @property
    def qualified_name(self) -> str:
        return f"{self.namespace}/{self.name}" if self.namespace else self.name


@dataclass
class FunctionInvocation:
    """Represents a function or constructor call in the code."""

    caller_name: str
    target_name: str
    location: SourceLocation
    argument_count: int = 0
    argument_snippets: list[str] = field(default_factory=list)


@dataclass
class ExpressionFlowStep:
    """Represents a fine-grained value/expression flow step inside a function."""

    source_expr: str  # e.g. 'request.json["user_id"]', 'repository.find(user_id)', 'user.email'
    target_expr: str  # e.g. 'user_id', 'user', 'email'
    step_kind: str  # 'assign', 'attribute', 'subscript', 'call', 'return', 'param'
    location: SourceLocation
    call_target: str | None = None  # e.g. 'repository.find' if step_kind == 'call'
    call_args: list[str] = field(default_factory=list)  # e.g. ['user_id']


@dataclass
class FunctionModel(NamedCodeEntity):
    """Represents a function, method, multimethod implementation, or macro."""

    location: SourceLocation = field(default_factory=lambda: SourceLocation(file_path="", line=1, column=1))
    docstring: str | None = None
    is_private: bool = False
    is_abstract: bool = False
    is_macro: bool = False
    is_multimethod: bool = False
    dispatch_fn: str | None = None
    dispatch_val: str | None = None
    parent_multimethod: str | None = None
    parameter_lists: list[list[str]] = field(default_factory=list)
    body_text: str = ""
    calls: list[str] = field(default_factory=list)
    invocations: list[FunctionInvocation] = field(default_factory=list)
    flow_steps: list[ExpressionFlowStep] = field(default_factory=list)
    returns_closure: bool = False
    instantiates_types: list[str] = field(default_factory=list)
    reads_variables: list[str] = field(default_factory=list)
    writes_variables: list[str] = field(default_factory=list)
    modifies_variables: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class ProtocolModel(NamedCodeEntity):
    """Represents a protocol, interface, or abstract trait definition."""

    location: SourceLocation = field(default_factory=lambda: SourceLocation(file_path="", line=1, column=1))
    docstring: str | None = None
    methods: list[MethodSignature] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    def has_method(self, name: str) -> bool:
        return any(m.name == name for m in self.methods)


@dataclass
class RecordModel(NamedCodeEntity):
    """Represents a defrecord, deftype, or class struct."""

    location: SourceLocation = field(default_factory=lambda: SourceLocation(file_path="", line=1, column=1))
    fields: list[str] = field(default_factory=list)
    implemented_protocols: list[str] = field(default_factory=list)
    methods: list[FunctionModel] = field(default_factory=list)
    is_type: bool = False
    docstring: str | None = None

    def implements_protocol(self, protocol_name: str) -> bool:
        norm = protocol_name.split("/")[-1]
        return any(p == protocol_name or p.split("/")[-1] == norm for p in self.implemented_protocols)


@dataclass
class ProtocolExtensionModel:
    """Represents an external protocol extension (extend-type / extend-protocol)."""

    target_type: str
    protocol_name: str
    namespace: str
    location: SourceLocation
    methods: list[FunctionModel] = field(default_factory=list)


@dataclass
class StateModel(NamedCodeEntity):
    """Represents a state holder or global binding (atom, ref, agent, defonce, var)."""

    location: SourceLocation = field(default_factory=lambda: SourceLocation(file_path="", line=1, column=1))
    kind: str = "atom"  # "atom", "ref", "agent", "var", "defonce", "delay", "promise"
    initial_expr: str | None = None
    is_once: bool = False
    is_dynamic: bool = False
    watchers: list[str] = field(default_factory=list)


@dataclass
class WatchModel:
    """Represents an observer watcher subscription (add-watch)."""

    target_state_name: str
    watch_key: str
    callback_fn_name: str
    location: SourceLocation


@dataclass
class NamespaceModel:
    """Represents a single namespace / file module."""

    name: str
    file_path: str
    docstring: str | None = None
    requires: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    protocols: dict[str, ProtocolModel] = field(default_factory=dict)
    records: dict[str, RecordModel] = field(default_factory=dict)
    extensions: list[ProtocolExtensionModel] = field(default_factory=list)
    functions: dict[str, FunctionModel] = field(default_factory=dict)
    multimethods: dict[str, list[FunctionModel]] = field(default_factory=dict)
    states: dict[str, StateModel] = field(default_factory=dict)
    watches: list[WatchModel] = field(default_factory=list)


@dataclass
class CodeModel:
    """Aggregate Root representing the whole scanned codebase."""

    namespaces: dict[str, NamespaceModel] = field(default_factory=dict)
    _all_functions_cache: list[FunctionModel] | None = field(default=None, init=False, repr=False)
    _all_protocols_cache: list[ProtocolModel] | None = field(default=None, init=False, repr=False)
    _all_records_cache: list[RecordModel] | None = field(default=None, init=False, repr=False)
    _implements_cache: dict[str, list[RecordModel]] | None = field(default=None, init=False, repr=False)

    def _invalidate_caches(self) -> None:
        self._all_functions_cache = None
        self._all_protocols_cache = None
        self._all_records_cache = None
        self._implements_cache = None

    def add_namespace(self, ns: NamespaceModel) -> None:
        self._invalidate_caches()
        if ns.name in self.namespaces:
            existing = self.namespaces[ns.name]
            existing.requires.extend([r for r in ns.requires if r not in existing.requires])
            existing.imports.extend([i for i in ns.imports if i not in existing.imports])
            existing.protocols.update(ns.protocols)
            existing.records.update(ns.records)
            existing.extensions.extend(ns.extensions)
            existing.functions.update(ns.functions)
            for k, v in ns.multimethods.items():
                existing.multimethods.setdefault(k, []).extend(v)
            existing.states.update(ns.states)
            existing.watches.extend(ns.watches)
        else:
            self.namespaces[ns.name] = ns

    def get_namespace(self, name: str) -> NamespaceModel | None:
        return self.namespaces.get(name)

    def all_file_paths(self) -> set[str]:
        files: set[str] = set()
        for ns in self.namespaces.values():
            self._collect_ns_files(ns, files)
        return files

    def _collect_ns_files(self, ns: NamespaceModel, files: set[str]) -> None:
        if ns.file_path:
            files.add(ns.file_path)
        items = list(ns.records.values()) + list(ns.protocols.values()) + list(ns.functions.values())
        for item in items:
            if item.location and item.location.file_path:
                files.add(item.location.file_path)

    def all_functions(self) -> list[FunctionModel]:
        if self._all_functions_cache is not None:
            return self._all_functions_cache

        res: list[FunctionModel] = []
        seen: set[tuple[str, str, int]] = set()
        for ns in self.namespaces.values():
            self._collect_ns_functions(ns, res, seen)
        self._all_functions_cache = res
        return res

    def _collect_ns_functions(
        self, ns: NamespaceModel, res: list[FunctionModel], seen: set[tuple[str, str, int]]
    ) -> None:
        candidates = list(ns.functions.values())
        for mm_methods in ns.multimethods.values():
            candidates.extend(mm_methods)
        for rec in ns.records.values():
            candidates.extend(rec.methods)
        for ext in ns.extensions:
            candidates.extend(ext.methods)

        for fn in candidates:
            loc_path = fn.location.file_path if fn.location else ""
            loc_line = fn.location.line if fn.location else 1
            key = (fn.name, loc_path, loc_line)
            if key not in seen:
                seen.add(key)
                res.append(fn)

    def all_protocols(self) -> list[ProtocolModel]:
        if self._all_protocols_cache is not None:
            return self._all_protocols_cache
        res: list[ProtocolModel] = []
        for ns in self.namespaces.values():
            res.extend(ns.protocols.values())
        self._all_protocols_cache = res
        return res

    def all_records(self) -> list[RecordModel]:
        if self._all_records_cache is not None:
            return self._all_records_cache
        res: list[RecordModel] = []
        for ns in self.namespaces.values():
            res.extend(ns.records.values())
        self._all_records_cache = res
        return res

    def all_extensions(self) -> list[ProtocolExtensionModel]:
        res: list[ProtocolExtensionModel] = []
        for ns in self.namespaces.values():
            res.extend(ns.extensions)
        return res

    def all_states(self) -> list[StateModel]:
        res: list[StateModel] = []
        for ns in self.namespaces.values():
            res.extend(ns.states.values())
        return res

    def all_watches(self) -> list[WatchModel]:
        res: list[WatchModel] = []
        for ns in self.namespaces.values():
            res.extend(ns.watches)
        return res

    def find_protocol(self, name: str) -> ProtocolModel | None:
        norm = name.split("/")[-1]
        for ns in self.namespaces.values():
            if name in ns.protocols:
                return ns.protocols[name]
            for p_name, proto in ns.protocols.items():
                if p_name == norm or proto.name == norm:
                    return proto
        return None

    def find_function(self, name: str) -> FunctionModel | None:
        """Look up a function by short name, qualified name, or partial match."""
        norm = name.split("/")[-1]
        for ns in self.namespaces.values():
            if name in ns.functions:
                return ns.functions[name]
            for fn_name, fn in ns.functions.items():
                if fn_name == norm or fn.name == norm or fn.name.endswith(f".{norm}"):
                    return fn
        return None

    def find_records_implementing(self, protocol_name: str) -> list[RecordModel]:
        if self._implements_cache is None:
            self._implements_cache = {}
            for rec in self.all_records():
                for proto in rec.implemented_protocols:
                    self._implements_cache.setdefault(proto, []).append(rec)
        norm = protocol_name.split("/")[-1]
        matches: list[RecordModel] = []
        for rec in self.all_records():
            for p in rec.implemented_protocols:
                if p == protocol_name or p.split("/")[-1] == norm:
                    matches.append(rec)
                    break
        return matches

    def find_callers_of(self, fn_name: str) -> list[FunctionModel]:
        norm = fn_name.split("/")[-1]
        callers: list[FunctionModel] = []
        for fn in self.all_functions():
            if any(call == fn_name or call.split("/")[-1] == norm for call in fn.calls):
                callers.append(fn)
        return callers

    # -------------------------------------------------------------------------
    # Graph & Cross-Namespace Dependency Analysis
    # -------------------------------------------------------------------------

    def build_namespace_dependency_graph(self) -> dict[str, set[str]]:
        """Build directed adjacency map of namespace dependencies: source_ns -> {target_ns, ...}."""
        graph: dict[str, set[str]] = {ns_name: set() for ns_name in self.namespaces}
        all_ns_names = set(self.namespaces.keys())

        for ns_name, ns in self.namespaces.items():
            self._connect_import_dependencies(ns_name, ns, graph)
            self._connect_call_dependencies(ns_name, ns, all_ns_names, graph)

        return graph

    def _connect_import_dependencies(self, ns_name: str, ns: NamespaceModel, graph: dict[str, set[str]]) -> None:
        all_imported_symbols = set(ns.requires) | set(ns.imports)
        for raw_sym in all_imported_symbols:
            sym_clean = os.path.splitext(os.path.basename(raw_sym))[0]
            for other_name, other_ns in self.namespaces.items():
                if other_name == ns_name:
                    continue
                other_base = (
                    os.path.splitext(os.path.basename(other_ns.file_path))[0] if other_ns.file_path else other_name
                )
                if (
                    sym_clean == other_name
                    or sym_clean == other_base
                    or sym_clean in other_ns.records
                    or raw_sym in other_ns.records
                ):
                    graph[ns_name].add(other_name)

    def _connect_call_dependencies(
        self, ns_name: str, ns: NamespaceModel, all_ns_names: set[str], graph: dict[str, set[str]]
    ) -> None:
        for fn in ns.functions.values():
            for call in fn.calls:
                prefix = call.split(".")[0] if "." in call else (call.split("::")[0] if "::" in call else None)
                if prefix and prefix in all_ns_names and prefix != ns_name:
                    graph[ns_name].add(prefix)

    def find_circular_dependencies(self) -> list[list[str]]:
        """Detect all simple circular dependency cycles between namespaces."""
        graph = self.build_namespace_dependency_graph()
        cycles: list[list[str]] = []
        visited: set[str] = set()

        def _dfs(current: str, path: list[str], path_set: set[str]) -> None:
            path.append(current)
            path_set.add(current)

            for neighbor in sorted(graph.get(current, set())):
                if neighbor == path[0] and len(path) >= 2:
                    # Found cycle back to origin
                    cycles.append(list(path))
                elif neighbor not in path_set and neighbor not in visited:
                    _dfs(neighbor, path, path_set)

            path.pop()
            path_set.remove(current)

        for node in sorted(graph.keys()):
            _dfs(node, [], set())
            visited.add(node)

        # Deduplicate rotationally equivalent cycles
        unique_cycles: list[list[str]] = []
        seen_cycle_keys: set[tuple[str, ...]] = set()

        for c in cycles:
            if "global" in c:
                continue
            # Canonical cycle representation by smallest element first
            min_idx = c.index(min(c))
            canonical = tuple(c[min_idx:] + c[:min_idx])
            if canonical not in seen_cycle_keys:
                seen_cycle_keys.add(canonical)
                unique_cycles.append(c)

        return unique_cycles
