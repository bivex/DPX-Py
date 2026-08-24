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
        max_depth: int = 15,
    ) -> DataFlowGraph:
        """Trace forward data flow: what reads and propagates root_variable."""
        graph = DataFlowGraph(
            root_id=root_variable,
            direction=DataFlowDirection.OUT,
            variant=variant,
        )

        # Register root variable
        graph.add_node(
            node_id=root_variable,
            name=root_variable,
            kind=NodeKind.VARIABLE,
            is_root=True,
        )

        # Pre-build / retrieve cached inverted index for O(1) reader lookups
        if not hasattr(model, "_readers_by_var"):
            readers_by_var: dict[str, list] = defaultdict(list)
            for fn in model.all_functions():
                for r_var in fn.reads_variables:
                    readers_by_var[r_var].append(fn)
            model._readers_by_var = readers_by_var  # type: ignore[attr-defined]
        readers_by_var = model._readers_by_var  # type: ignore[attr-defined]

        # Fallback for dynamic variables in body text if not in parsed reads
        if not readers_by_var.get(root_variable):
            for fn in model.all_functions():
                if root_variable in fn.body_text:
                    readers_by_var[root_variable].append(fn)

        visited_vars: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(root_variable, 0)])

        while queue:
            var_name, depth = queue.popleft()
            if depth >= max_depth:
                continue
            graph.max_depth = max(graph.max_depth, depth)

            if var_name in visited_vars and depth > 0:
                continue
            visited_vars.add(var_name)

            reader_functions = readers_by_var.get(var_name, [])

            for fn in reader_functions:
                fn_id = f"fn_{fn.name}"
                cluster_name = fn.namespace or (fn.location.file_path.split("/")[-1] if fn.location else "global")
                graph.add_node(
                    node_id=fn_id,
                    name=fn.name,
                    kind=NodeKind.FUNCTION,
                    cluster=cluster_name,
                    file_path=fn.location.file_path if fn.location else "",
                    line=fn.location.line if fn.location else 1,
                )
                graph.add_edge(from_id=var_name, to_id=fn_id, kind="READS", location=fn.location)

                # 2. Check what variables this function writes or modifies
                written_vars = list(dict.fromkeys(fn.writes_variables + fn.modifies_variables))

                for w_var in written_vars:
                    w_kind = "MODIFIES" if w_var in fn.modifies_variables or (w_var == var_name) else "WRITES"
                    graph.add_node(
                        node_id=w_var,
                        name=w_var,
                        kind=NodeKind.VARIABLE,
                        cluster=cluster_name,
                    )
                    graph.add_edge(from_id=fn_id, to_id=w_var, kind=w_kind, location=fn.location)

                    if w_var != var_name and w_var not in visited_vars:
                        queue.append((w_var, depth + 1))

        return graph

    def trace_data_flow_in(
        self,
        model: CodeModel,
        root_variable: str,
        variant: DataFlowVariant = DataFlowVariant.SIMPLIFIED,
        max_depth: int = 15,
    ) -> DataFlowGraph:
        """Trace backward data flow: what produces/modifies root_variable."""
        graph = DataFlowGraph(
            root_id=root_variable,
            direction=DataFlowDirection.IN,
            variant=variant,
        )

        graph.add_node(
            node_id=root_variable,
            name=root_variable,
            kind=NodeKind.VARIABLE,
            is_root=True,
        )

        # Pre-build / retrieve cached inverted index for O(1) writer lookups
        if not hasattr(model, "_writers_by_var"):
            writers_by_var: dict[str, list] = defaultdict(list)
            for fn in model.all_functions():
                for w_var in fn.writes_variables + fn.modifies_variables:
                    writers_by_var[w_var].append(fn)
            model._writers_by_var = writers_by_var  # type: ignore[attr-defined]
        writers_by_var = model._writers_by_var  # type: ignore[attr-defined]

        visited_vars: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(root_variable, 0)])

        while queue:
            var_name, depth = queue.popleft()
            if depth >= max_depth:
                continue
            graph.max_depth = max(graph.max_depth, depth)

            if var_name in visited_vars and depth > 0:
                continue
            visited_vars.add(var_name)

            writer_functions = writers_by_var.get(var_name, [])

            for fn in writer_functions:
                fn_id = f"fn_{fn.name}"
                cluster_name = fn.namespace or (fn.location.file_path.split("/")[-1] if fn.location else "global")
                graph.add_node(
                    node_id=fn_id,
                    name=fn.name,
                    kind=NodeKind.FUNCTION,
                    cluster=cluster_name,
                    file_path=fn.location.file_path if fn.location else "",
                    line=fn.location.line if fn.location else 1,
                )
                w_kind = "MODIFIED_BY" if var_name in fn.modifies_variables else "WRITTEN_BY"
                graph.add_edge(from_id=var_name, to_id=fn_id, kind=w_kind, location=fn.location)

                # 2. Find variables that this function reads
                for r_var in fn.reads_variables:
                    graph.add_node(
                        node_id=r_var,
                        name=r_var,
                        kind=NodeKind.VARIABLE,
                        cluster=cluster_name,
                    )
                    graph.add_edge(from_id=fn_id, to_id=r_var, kind="READS_FROM", location=fn.location)

                    if r_var != var_name and r_var not in visited_vars:
                        queue.append((r_var, depth + 1))

        return graph

    def trace_relationship(
        self,
        model: CodeModel,
        source: str,
        target: str,
        max_depth: int = 15,
    ) -> DataFlowGraph:
        """Trace paths specifically connecting source and target entities (Relationship variant)."""
        full_out_graph = self.trace_data_flow_out(model, source, variant=DataFlowVariant.RELATIONSHIP, max_depth=max_depth)

        # Filter nodes and edges to only those that lie on paths from source to target
        adj: dict[str, list[str]] = {}
        for edge in full_out_graph.edges:
            adj.setdefault(edge.from_id, []).append(edge.to_id)

        target_nodes = {target, f"fn_{target}"}

        # Backtrack DFS to find all reachable nodes to target
        reachable_to_target: set[str] = set()

        def can_reach(u: str, path: list[str]) -> bool:
            if u in target_nodes:
                reachable_to_target.update(path + [u])
                return True
            found = False
            for v in adj.get(u, []):
                if v not in path and can_reach(v, path + [u]):
                    found = True
            return found

        can_reach(source, [])

        filtered_graph = DataFlowGraph(
            root_id=source,
            direction=DataFlowDirection.OUT,
            variant=DataFlowVariant.RELATIONSHIP,
        )

        for node_id in reachable_to_target:
            if node_id in full_out_graph.nodes:
                node = full_out_graph.nodes[node_id]
                filtered_graph.add_node(
                    node_id=node.id,
                    name=node.name,
                    kind=node.kind,
                    cluster=node.cluster,
                    file_path=node.file_path,
                    line=node.line,
                    is_root=node.is_root,
                )

        for edge in full_out_graph.edges:
            if edge.from_id in reachable_to_target and edge.to_id in reachable_to_target:
                filtered_graph.add_edge(edge.from_id, edge.to_id, edge.kind, edge.location)

        return filtered_graph

    def analyze_all_variables(
        self,
        model: CodeModel,
        target_path: str = "",
        direction: DataFlowDirection = DataFlowDirection.OUT,
        file_filter: str | None = None,
        max_depth: int = 15,
    ) -> DataFlowSummaryReport:
        """Analyze data flow for all discovered variables in the model or specific file."""
        from pattern_detector.domain.data_flow import DataFlowSummaryReport, VariableFlowSummary

        RESERVED = {"true", "false", "nullptr", "NULL", "std", "this", "auto", "void", "int", "char", "bool", "double", "float", "size_t", "const"}
        vars_map: dict[str, Any] = {}
        for s in model.all_states():
            if file_filter and s.location and file_filter not in s.location.file_path:
                continue
            if s.name and len(s.name) >= 2 and s.name not in RESERVED and (s.name[0].isalpha() or s.name[0] == '_'):
                vars_map[s.name] = s.location

        for r in model.all_records():
            if file_filter and r.location and file_filter not in r.location.file_path:
                continue
            for f in r.fields:
                if f and len(f) >= 2 and f not in vars_map and f not in RESERVED and (f[0].isalpha() or f[0] == '_'):
                    vars_map[f] = r.location

        for fn in model.all_functions():
            if file_filter and fn.location and file_filter not in fn.location.file_path:
                continue
            for v in fn.reads_variables + fn.writes_variables + fn.modifies_variables:
                if v and len(v) >= 2 and v not in vars_map and v not in RESERVED and (v[0].isalpha() or v[0] == '_'):
                    vars_map[v] = fn.location

        summaries: list[VariableFlowSummary] = []
        total_edges_sum = 0

        for var_name, loc in vars_map.items():
            if direction == DataFlowDirection.IN:
                graph = self.trace_data_flow_in(model, var_name, max_depth=max_depth)
            else:
                graph = self.trace_data_flow_out(model, var_name, max_depth=max_depth)

            # Extract readers and writers
            readers = [
                e.to_id.replace("fn_", "") for e in graph.edges if e.from_id == var_name and e.kind == "READS"
            ] if direction == DataFlowDirection.OUT else [
                e.to_id for e in graph.edges if e.from_id != var_name and e.kind == "READS_FROM"
            ]

            writers = [
                e.from_id.replace("fn_", "") for e in graph.edges if e.to_id == var_name and e.kind in ("WRITES", "MODIFIES")
            ] if direction == DataFlowDirection.OUT else [
                e.to_id.replace("fn_", "") for e in graph.edges if e.from_id == var_name and e.kind in ("WRITTEN_BY", "MODIFIED_BY")
            ]

            reach = len(graph.nodes) - 1  # exclude root itself
            total_edges_sum += len(graph.edges)
            m_depth = graph.max_depth

            # Determine impact level
            if reach >= 6 or m_depth >= 4:
                impact = "CRITICAL"
            elif reach >= 3 or m_depth >= 2:
                impact = "HIGH"
            elif reach >= 1 or len(readers) >= 1:
                impact = "MEDIUM"
            else:
                impact = "LOW"

            summaries.append(
                VariableFlowSummary(
                    name=var_name,
                    file_path=loc.file_path if loc else "",
                    line=loc.line if loc else 1,
                    readers=sorted(dict.fromkeys(readers)),
                    writers=sorted(dict.fromkeys(writers)),
                    downstream_reach=reach,
                    max_depth=m_depth,
                    impact_level=impact,
                    graph=graph,
                )
            )

        return DataFlowSummaryReport(
            target_path=target_path,
            direction=direction,
            summaries=summaries,
            total_variables=len(summaries),
            total_edges=total_edges_sum,
        )
