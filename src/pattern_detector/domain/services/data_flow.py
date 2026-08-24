"""Data Flow Analysis Service (SciTools Understand Parity)."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.data_flow import (
    DataFlowDirection,
    DataFlowGraph,
    DataFlowSummaryReport,
    DataFlowVariant,
    NodeKind,
    VariableFlowSummary,
)


class DataFlowService:
    """Domain Service for computing Forward (Data Flow Out) and Backward (Data Flow In) graphs."""

    def trace_data_flow_out(
        self,
        model: CodeModel,
        root_variable: str,
        variant: DataFlowVariant = DataFlowVariant.SIMPLIFIED,
        max_depth: int = 6,
        max_nodes: int = 50,
    ) -> DataFlowGraph:
        """Trace forward data flow: what reads and propagates root_variable."""
        graph = self._create_initial_graph(root_variable, DataFlowDirection.OUT, variant)
        readers_by_var = self._get_readers_index(model, root_variable)

        visited_vars: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(root_variable, 0)])

        while queue and len(graph.nodes) < max_nodes:
            var_name, depth = queue.popleft()
            if depth >= max_depth or (var_name in visited_vars and depth > 0):
                continue
            graph.max_depth = max(graph.max_depth, depth)
            visited_vars.add(var_name)

            for fn in readers_by_var.get(var_name, []):
                if len(graph.nodes) >= max_nodes:
                    break
                self._expand_forward_function(graph, var_name, fn, depth, max_nodes, visited_vars, queue)

        return graph

    def trace_data_flow_in(
        self,
        model: CodeModel,
        root_variable: str,
        variant: DataFlowVariant = DataFlowVariant.SIMPLIFIED,
        max_depth: int = 6,
        max_nodes: int = 50,
    ) -> DataFlowGraph:
        """Trace backward data flow: what produces/modifies root_variable."""
        graph = self._create_initial_graph(root_variable, DataFlowDirection.IN, variant)
        writers_by_var = self._get_writers_index(model)

        visited_vars: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(root_variable, 0)])

        while queue and len(graph.nodes) < max_nodes:
            var_name, depth = queue.popleft()
            if depth >= max_depth or (var_name in visited_vars and depth > 0):
                continue
            graph.max_depth = max(graph.max_depth, depth)
            visited_vars.add(var_name)

            for fn in writers_by_var.get(var_name, []):
                if len(graph.nodes) >= max_nodes:
                    break
                self._expand_backward_function(graph, var_name, fn, depth, max_nodes, visited_vars, queue)

        return graph

    def trace_relationship_path(
        self,
        model: CodeModel,
        source_variable: str,
        target_variable: str,
        max_depth: int = 10,
    ) -> DataFlowGraph:
        """Find the shortest data flow path from source_variable to target_variable."""
        full_out_graph = self.trace_data_flow_out(model, source_variable, max_depth=max_depth)

        filtered_graph = DataFlowGraph(
            root_id=source_variable,
            direction=DataFlowDirection.OUT,
            variant=DataFlowVariant.RELATIONSHIP,
        )

        if target_variable not in full_out_graph.nodes:
            if source_variable in full_out_graph.nodes:
                filtered_graph.add_node(node_id=source_variable, name=source_variable, kind=NodeKind.VARIABLE, is_root=True)
            return filtered_graph

        reachable_to_target = self._find_ancestors(full_out_graph, target_variable)
        self._populate_subgraph(full_out_graph, filtered_graph, reachable_to_target)
        return filtered_graph

    def trace_relationship(
        self,
        model: CodeModel,
        source: str,
        target: str,
        max_depth: int = 10,
    ) -> DataFlowGraph:
        """Trace paths specifically connecting source and target entities (Relationship variant)."""
        g = self.trace_relationship_path(model, source, target, max_depth=max_depth)
        g.variant = DataFlowVariant.RELATIONSHIP
        return g

    def analyze_all_variables(
        self,
        model: CodeModel,
        target_path: str = "",
        direction: DataFlowDirection = DataFlowDirection.OUT,
        file_filter: str | None = None,
        max_depth: int = 6,
    ) -> DataFlowSummaryReport:
        """Analyze data flow for all discovered variables in the model or specific file."""
        vars_map = self._collect_model_variables(model, file_filter)
        summaries: list[VariableFlowSummary] = []
        total_edges_sum = 0

        for var_name, loc in vars_map.items():
            graph = (
                self.trace_data_flow_in(model, var_name, max_depth=max_depth)
                if direction == DataFlowDirection.IN
                else self.trace_data_flow_out(model, var_name, max_depth=max_depth)
            )
            summary = self._summarize_variable_flow(var_name, loc, graph)
            summaries.append(summary)
            total_edges_sum += len(graph.edges)

        return DataFlowSummaryReport(
            target_path=target_path,
            direction=direction,
            summaries=summaries,
            total_variables=len(summaries),
            total_edges=total_edges_sum,
        )

    # ── Private Helper Functions for Complexity Reduction ───────────

    def _create_initial_graph(self, root_variable: str, direction: DataFlowDirection, variant: DataFlowVariant) -> DataFlowGraph:
        graph = DataFlowGraph(root_id=root_variable, direction=direction, variant=variant)
        graph.add_node(node_id=root_variable, name=root_variable, kind=NodeKind.VARIABLE, is_root=True)
        return graph

    def _get_readers_index(self, model: CodeModel, root_variable: str) -> dict[str, list]:
        if not hasattr(model, "_readers_by_var"):
            readers_by_var: dict[str, list] = defaultdict(list)
            for fn in model.all_functions():
                for r_var in fn.reads_variables:
                    readers_by_var[r_var].append(fn)
            model._readers_by_var = readers_by_var  # type: ignore[attr-defined]
        index: dict[str, list] = model._readers_by_var  # type: ignore[attr-defined]

        if not index.get(root_variable):
            for fn in model.all_functions():
                if root_variable in fn.body_text:
                    index[root_variable].append(fn)
        return index

    def _get_writers_index(self, model: CodeModel) -> dict[str, list]:
        if not hasattr(model, "_writers_by_var"):
            writers_by_var: dict[str, list] = defaultdict(list)
            for fn in model.all_functions():
                for w_var in fn.writes_variables + fn.modifies_variables:
                    writers_by_var[w_var].append(fn)
            model._writers_by_var = writers_by_var  # type: ignore[attr-defined]
        return model._writers_by_var  # type: ignore[attr-defined]

    def _expand_forward_function(
        self, graph: DataFlowGraph, var_name: str, fn: Any, depth: int, max_nodes: int,
        visited_vars: set[str], queue: deque[tuple[str, int]]
    ) -> None:
        fn_id = f"fn_{fn.name}"
        cluster_name = fn.namespace or (fn.location.file_path.split("/")[-1] if fn.location else "global")
        graph.add_node(
            node_id=fn_id, name=fn.name, kind=NodeKind.FUNCTION, cluster=cluster_name,
            file_path=fn.location.file_path if fn.location else "", line=fn.location.line if fn.location else 1,
        )
        graph.add_edge(from_id=var_name, to_id=fn_id, kind="READS", location=fn.location)

        written_vars = list(dict.fromkeys(fn.writes_variables + fn.modifies_variables))
        for w_var in written_vars:
            if len(graph.nodes) >= max_nodes:
                break
            w_kind = "MODIFIES" if w_var in fn.modifies_variables or (w_var == var_name) else "WRITES"
            graph.add_node(node_id=w_var, name=w_var, kind=NodeKind.VARIABLE, cluster=cluster_name)
            graph.add_edge(from_id=fn_id, to_id=w_var, kind=w_kind, location=fn.location)

            if w_var != var_name and w_var not in visited_vars:
                queue.append((w_var, depth + 1))

    def _expand_backward_function(
        self, graph: DataFlowGraph, var_name: str, fn: Any, depth: int, max_nodes: int,
        visited_vars: set[str], queue: deque[tuple[str, int]]
    ) -> None:
        fn_id = f"fn_{fn.name}"
        cluster_name = fn.namespace or (fn.location.file_path.split("/")[-1] if fn.location else "global")
        graph.add_node(
            node_id=fn_id, name=fn.name, kind=NodeKind.FUNCTION, cluster=cluster_name,
            file_path=fn.location.file_path if fn.location else "", line=fn.location.line if fn.location else 1,
        )
        w_kind = "MODIFIED_BY" if var_name in fn.modifies_variables else "WRITTEN_BY"
        graph.add_edge(from_id=var_name, to_id=fn_id, kind=w_kind, location=fn.location)

        for r_var in fn.reads_variables:
            if len(graph.nodes) >= max_nodes:
                break
            graph.add_node(node_id=r_var, name=r_var, kind=NodeKind.VARIABLE, cluster=cluster_name)
            graph.add_edge(from_id=fn_id, to_id=r_var, kind="READS_FROM", location=fn.location)

            if r_var != var_name and r_var not in visited_vars:
                queue.append((r_var, depth + 1))

    def _find_ancestors(self, graph: DataFlowGraph, target: str) -> set[str]:
        reverse_adj: dict[str, list[str]] = defaultdict(list)
        for edge in graph.edges:
            reverse_adj[edge.to_id].append(edge.from_id)

        ancestors: set[str] = set()
        q: deque[str] = deque([target])
        while q:
            curr = q.popleft()
            if curr in ancestors:
                continue
            ancestors.add(curr)
            for prev in reverse_adj.get(curr, []):
                q.append(prev)
        return ancestors

    def _populate_subgraph(self, src_graph: DataFlowGraph, dst_graph: DataFlowGraph, keep_nodes: set[str]) -> None:
        for node_id in keep_nodes:
            if node_id in src_graph.nodes:
                n = src_graph.nodes[node_id]
                dst_graph.add_node(node_id=n.id, name=n.name, kind=n.kind, cluster=n.cluster, file_path=n.file_path, line=n.line, is_root=n.is_root)
        for edge in src_graph.edges:
            if edge.from_id in keep_nodes and edge.to_id in keep_nodes:
                dst_graph.add_edge(edge.from_id, edge.to_id, edge.kind, edge.location)

    def _collect_model_variables(self, model: CodeModel, file_filter: str | None) -> dict[str, Any]:
        from pattern_detector.adapters.outbound.python_ast.py_parser_adapter import _PYTHON_BUILTINS_AND_KEYWORDS

        vars_map: dict[str, Any] = {}
        for s in model.all_states():
            if self._is_valid_var(s.name, s.location, file_filter, _PYTHON_BUILTINS_AND_KEYWORDS):
                vars_map[s.name] = s.location

        for r in model.all_records():
            if file_filter and r.location and file_filter not in r.location.file_path:
                continue
            for f in r.fields:
                if f not in vars_map and self._is_valid_var(f, r.location, file_filter, _PYTHON_BUILTINS_AND_KEYWORDS):
                    vars_map[f] = r.location

        for fn in model.all_functions():
            if file_filter and fn.location and file_filter not in fn.location.file_path:
                continue
            for v in fn.reads_variables + fn.writes_variables + fn.modifies_variables:
                if v not in vars_map and self._is_valid_var(v, fn.location, file_filter, _PYTHON_BUILTINS_AND_KEYWORDS):
                    vars_map[v] = fn.location

        return vars_map

    def _is_valid_var(self, name: str, loc: Any, file_filter: str | None, builtins: frozenset[str]) -> bool:
        if not name or len(name) < 2 or name in builtins or not (name[0].isalpha() or name[0] == "_"):
            return False
        return not (file_filter and loc and file_filter not in loc.file_path)

    def _summarize_variable_flow(self, var_name: str, loc: Any, graph: DataFlowGraph) -> VariableFlowSummary:
        readers = [e.to_id.replace("fn_", "") for e in graph.edges if e.from_id == var_name and e.kind == "READS"]
        writers = [e.from_id.replace("fn_", "") for e in graph.edges if e.to_id == var_name and e.kind in ("WRITES", "MODIFIES")]

        reach = len(graph.nodes) - 1
        impact = "HIGH" if reach >= 15 or len(readers) >= 5 else ("MEDIUM" if reach >= 4 or len(readers) >= 2 else "LOW")

        return VariableFlowSummary(
            name=var_name,
            file_path=loc.file_path if loc else "",
            line=loc.line if loc else 1,
            readers=sorted(set(readers)),
            writers=sorted(set(writers)),
            downstream_reach=reach,
            max_depth=graph.max_depth,
            impact_level=impact,
            graph=graph,
        )
