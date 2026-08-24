"""Data Flow Analysis Service (SciTools Understand Parity)."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
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
from pattern_detector.domain.taint import (
    DEFAULT_TAINT_SINKS,
    DEFAULT_TAINT_SOURCES,
    TaintFlow,
    TaintFlowStep,
    TaintSinkPattern,
    TaintSourcePattern,
)
from pattern_detector.domain.value_objects import SourceLocation


@dataclass
class _ExpansionContext:
    graph: DataFlowGraph
    depth: int
    max_nodes: int
    visited_vars: set[str]
    queue: deque[tuple[str, int]]
    model: CodeModel | None = None


class DataFlowService:
    """Domain Service for computing Forward (Data Flow Out), Backward (Data Flow In), and Taint Graphs."""

    def trace_data_flow_out(
        self,
        model: CodeModel,
        root_variable: str,
        variant: DataFlowVariant = DataFlowVariant.SIMPLIFIED,
        max_depth: int = 8,
        max_nodes: int = 50,
    ) -> DataFlowGraph:
        """Trace forward data flow: what reads, accesses, and propagates root_variable."""
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

            ctx = _ExpansionContext(
                graph=graph,
                depth=depth,
                max_nodes=max_nodes,
                visited_vars=visited_vars,
                queue=queue,
                model=model,
            )
            for fn in readers_by_var.get(var_name, []):
                if len(graph.nodes) >= max_nodes:
                    break
                self._expand_forward_function(ctx, var_name, fn)

        return graph

    def trace_data_flow_in(
        self,
        model: CodeModel,
        root_variable: str,
        variant: DataFlowVariant = DataFlowVariant.SIMPLIFIED,
        max_depth: int = 8,
        max_nodes: int = 50,
    ) -> DataFlowGraph:
        """Trace backward data flow: what produces/modifies/origins root_variable."""
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

            ctx = _ExpansionContext(
                graph=graph,
                depth=depth,
                max_nodes=max_nodes,
                visited_vars=visited_vars,
                queue=queue,
                model=model,
            )
            for fn in writers_by_var.get(var_name, []):
                if len(graph.nodes) >= max_nodes:
                    break
                self._expand_backward_function(ctx, var_name, fn)

        return graph

    def trace_relationship_path(
        self,
        model: CodeModel,
        source_variable: str,
        target_variable: str,
        max_depth: int = 12,
    ) -> DataFlowGraph:
        """Find the shortest data flow path from source_variable to target_variable."""
        full_out_graph = self.trace_data_flow_out(model, source_variable, max_depth=max_depth)

        filtered_graph = DataFlowGraph(
            root_id=source_variable,
            direction=DataFlowDirection.OUT,
            variant=DataFlowVariant.RELATIONSHIP,
        )

        matched_target_id = self._resolve_matching_node_id(full_out_graph, target_variable)
        if not matched_target_id:
            if source_variable in full_out_graph.nodes:
                filtered_graph.add_node(
                    node_id=source_variable, name=source_variable, kind=NodeKind.VARIABLE, is_root=True
                )
            return filtered_graph

        reachable_to_target = self._find_ancestors(full_out_graph, matched_target_id)
        self._populate_subgraph(full_out_graph, filtered_graph, reachable_to_target)
        return filtered_graph

    def trace_taint_flows(
        self,
        model: CodeModel,
        sources: tuple[TaintSourcePattern, ...] = DEFAULT_TAINT_SOURCES,
        sinks: tuple[TaintSinkPattern, ...] = DEFAULT_TAINT_SINKS,
    ) -> list[TaintFlow]:
        """Traces end-to-end untrusted or sensitive value flows from Sources to Sinks."""
        flows: list[TaintFlow] = []
        found_sources = self._discover_sources(model, sources)

        for src_name, src_pattern, src_loc in found_sources:
            out_graph = self.trace_data_flow_out(model, src_name, max_depth=10, max_nodes=50)
            for sink_pattern in sinks:
                matched_sink_id = self._find_sink_in_graph(out_graph, sink_pattern.pattern)
                if matched_sink_id:
                    path_graph = self.trace_relationship_path(model, src_name, matched_sink_id)
                    flow = self._build_taint_flow(
                        src_name, src_pattern, matched_sink_id, sink_pattern, path_graph, src_loc
                    )
                    flows.append(flow)
        return flows

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

    def _resolve_matching_node_id(self, graph: DataFlowGraph, target: str) -> str | None:
        if target in graph.nodes:
            return target
        for nid, node in graph.nodes.items():
            if target in node.name or target in nid:
                return nid
        return None

    def _find_sink_in_graph(self, graph: DataFlowGraph, sink_pattern: str) -> str | None:
        for nid, node in graph.nodes.items():
            if sink_pattern in node.name or sink_pattern in nid:
                return nid
        return None

    def _discover_sources(
        self, model: CodeModel, sources: tuple[TaintSourcePattern, ...]
    ) -> list[tuple[str, TaintSourcePattern, SourceLocation]]:
        discovered: list[tuple[str, TaintSourcePattern, SourceLocation]] = []
        seen: set[str] = set()

        for fn in model.all_functions():
            for step in fn.flow_steps:
                for sp in sources:
                    if sp.pattern in step.source_expr and step.source_expr not in seen:
                        seen.add(step.source_expr)
                        discovered.append((step.source_expr, sp, step.location))
            for r_var in fn.reads_variables:
                for sp in sources:
                    if sp.pattern in r_var and r_var not in seen:
                        seen.add(r_var)
                        discovered.append((r_var, sp, fn.location))
        return discovered

    def _build_taint_flow(
        self,
        src_name: str,
        src_pattern: TaintSourcePattern,
        sink_id: str,
        sink_pattern: TaintSinkPattern,
        path_graph: DataFlowGraph,
        src_loc: SourceLocation,
    ) -> TaintFlow:
        steps = self._build_taint_flow_steps(path_graph, sink_id)
        return TaintFlow(
            id=f"taint_{src_pattern.category.value}_{sink_pattern.category.value}_{len(steps)}",
            category=sink_pattern.category,
            severity=sink_pattern.severity,
            cwe_id=sink_pattern.cwe_id,
            source_expr=src_name,
            sink_target=sink_id,
            primary_location=src_loc,
            steps=steps,
            summary=f"Taint Flow: Untrusted input '{src_name}' flows directly into {sink_pattern.description} ('{sink_id}')",
            remediation_hint=f"Sanitize or validate '{src_name}' before passing it to '{sink_pattern.pattern}'.",
        )

    def _build_taint_flow_steps(self, path_graph: DataFlowGraph, sink_id: str) -> list[TaintFlowStep]:
        steps: list[TaintFlowStep] = []
        for idx, (nid, node) in enumerate(path_graph.nodes.items(), 1):
            kind_str = "SOURCE" if idx == 1 else ("SINK" if nid == sink_id else "FLOW")
            steps.append(
                TaintFlowStep(
                    step_number=idx,
                    expression=node.name,
                    kind=kind_str,
                    location=SourceLocation(file_path=node.file_path, line=node.line),
                    description=f"Value propagated to {node.kind.value} '{node.name}'",
                )
            )
        return steps

    def _create_initial_graph(
        self, root_variable: str, direction: DataFlowDirection, variant: DataFlowVariant
    ) -> DataFlowGraph:
        graph = DataFlowGraph(root_id=root_variable, direction=direction, variant=variant)
        is_src = any(sp.pattern in root_variable for sp in DEFAULT_TAINT_SOURCES)
        is_snk = any(sk.pattern in root_variable for sk in DEFAULT_TAINT_SINKS)
        graph.add_node(
            node_id=root_variable,
            name=root_variable,
            kind=NodeKind.SYMBOL,
            is_root=True,
            is_source=is_src,
            is_sink=is_snk,
        )
        return graph

    def _get_readers_index(self, model: CodeModel, root_variable: str) -> dict[str, list]:
        if not hasattr(model, "_readers_by_var"):
            model._readers_by_var = self._build_readers_index(model)  # type: ignore[attr-defined]
        index: dict[str, list] = model._readers_by_var  # type: ignore[attr-defined]
        if not index.get(root_variable):
            self._fill_readers_fallback(model, index, root_variable)
        return index

    def _build_readers_index(self, model: CodeModel) -> dict[str, list]:
        readers_by_var: dict[str, list] = defaultdict(list)
        for fn in model.all_functions():
            self._index_reads_variables(fn, readers_by_var)
            self._index_flow_step_sources(fn, readers_by_var)
        return readers_by_var

    def _index_reads_variables(self, fn: Any, index: dict[str, list]) -> None:
        for r_var in fn.reads_variables:
            index[r_var].append(fn)

    def _index_flow_step_sources(self, fn: Any, index: dict[str, list]) -> None:
        for step in fn.flow_steps:
            index[step.source_expr].append(fn)
            if step.step_kind == "call":
                for arg in step.call_args:
                    index[arg].append(fn)

    def _fill_readers_fallback(self, model: CodeModel, index: dict[str, list], root_variable: str) -> None:
        for fn in model.all_functions():
            if self._fn_mentions_variable(fn, root_variable):
                index[root_variable].append(fn)

    def _fn_mentions_variable(self, fn: Any, var: str) -> bool:
        if var in fn.body_text:
            return True
        return any(var in s.source_expr for s in fn.flow_steps)

    def _get_writers_index(self, model: CodeModel) -> dict[str, list]:
        if not hasattr(model, "_writers_by_var"):
            writers_by_var: dict[str, list] = defaultdict(list)
            for fn in model.all_functions():
                for w_var in fn.writes_variables + fn.modifies_variables:
                    writers_by_var[w_var].append(fn)
                for step in fn.flow_steps:
                    writers_by_var[step.target_expr].append(fn)
            model._writers_by_var = writers_by_var  # type: ignore[attr-defined]
        return model._writers_by_var  # type: ignore[attr-defined]

    def _expand_forward_function(
        self,
        ctx: _ExpansionContext,
        var_name: str,
        fn: Any,
    ) -> None:
        fn_id = f"fn_{fn.name}"
        cluster_name = fn.namespace or (fn.location.file_path.split("/")[-1] if fn.location else "global")
        ctx.graph.add_node(
            node_id=fn_id, name=fn.name, kind=NodeKind.FUNCTION, cluster=cluster_name, location=fn.location
        )
        ctx.graph.add_edge(from_id=var_name, to_id=fn_id, kind="READS", location=fn.location)

        # 1. Expand fine-grained flow steps
        self._expand_forward_flow_steps(ctx, var_name, fn, cluster_name)

        # 2. Def-Use fallback
        written_vars = list(dict.fromkeys(fn.writes_variables + fn.modifies_variables))
        for w_var in written_vars:
            if len(ctx.graph.nodes) >= ctx.max_nodes:
                break
            w_kind = "MODIFIES" if w_var in fn.modifies_variables or (w_var == var_name) else "WRITES"
            ctx.graph.add_node(node_id=w_var, name=w_var, kind=NodeKind.SYMBOL, cluster=cluster_name)
            ctx.graph.add_edge(from_id=fn_id, to_id=w_var, kind=w_kind, location=fn.location)

            if w_var != var_name and w_var not in ctx.visited_vars:
                ctx.queue.append((w_var, ctx.depth + 1))

    def _expand_forward_flow_steps(self, ctx: _ExpansionContext, var_name: str, fn: Any, cluster_name: str) -> None:
        for step in getattr(fn, "flow_steps", []):
            if len(ctx.graph.nodes) >= ctx.max_nodes:
                break
            if var_name in step.source_expr or var_name == step.source_expr:
                kind_map = {
                    "attribute": NodeKind.ATTRIBUTE,
                    "subscript": NodeKind.SUBSCRIPT,
                    "call": NodeKind.CALL,
                    "return": NodeKind.RETURN,
                    "param": NodeKind.PARAMETER,
                }
                n_kind = kind_map.get(step.step_kind, NodeKind.SYMBOL)
                is_snk = any(sk.pattern in step.target_expr for sk in DEFAULT_TAINT_SINKS)
                ctx.graph.add_node(
                    node_id=step.target_expr,
                    name=step.target_expr,
                    kind=n_kind,
                    cluster=cluster_name,
                    location=step.location,
                    is_sink=is_snk,
                )
                ctx.graph.add_edge(
                    from_id=var_name,
                    to_id=step.target_expr,
                    kind=step.step_kind.upper(),
                    location=step.location,
                )

                # Interprocedural link if call target is a known function in model
                if step.step_kind == "call" and step.call_target and ctx.model:
                    self._link_interprocedural_call(ctx, step, cluster_name)

                if step.target_expr != var_name and step.target_expr not in ctx.visited_vars:
                    ctx.queue.append((step.target_expr, ctx.depth + 1))

    def _link_interprocedural_call(self, ctx: _ExpansionContext, step: Any, cluster_name: str) -> None:
        if not ctx.model:
            return
        callee_fn = ctx.model.find_function(step.call_target)
        if callee_fn:
            callee_id = f"fn_{callee_fn.name}"
            ctx.graph.add_node(
                node_id=callee_id,
                name=callee_fn.name,
                kind=NodeKind.FUNCTION,
                cluster=callee_fn.namespace or cluster_name,
                location=callee_fn.location,
            )
            ctx.graph.add_edge(
                from_id=step.target_expr,
                to_id=callee_id,
                kind="CALLS",
                location=step.location,
            )
            params = callee_fn.parameter_lists[0] if callee_fn.parameter_lists else []
            for param in params:
                p_id = f"{callee_fn.name}.{param}"
                ctx.graph.add_node(
                    node_id=p_id,
                    name=p_id,
                    kind=NodeKind.PARAMETER,
                    cluster=callee_fn.namespace or cluster_name,
                    location=callee_fn.location,
                )
                ctx.graph.add_edge(from_id=callee_id, to_id=p_id, kind="PARAM_BIND", location=callee_fn.location)
                if p_id not in ctx.visited_vars:
                    ctx.queue.append((p_id, ctx.depth + 1))

    def _expand_backward_function(
        self,
        ctx: _ExpansionContext,
        var_name: str,
        fn: Any,
    ) -> None:
        fn_id = f"fn_{fn.name}"
        cluster_name = fn.namespace or (fn.location.file_path.split("/")[-1] if fn.location else "global")
        ctx.graph.add_node(
            node_id=fn_id, name=fn.name, kind=NodeKind.FUNCTION, cluster=cluster_name, location=fn.location
        )
        w_kind = "MODIFIED_BY" if var_name in fn.modifies_variables else "WRITTEN_BY"
        ctx.graph.add_edge(from_id=var_name, to_id=fn_id, kind=w_kind, location=fn.location)
        self._expand_backward_flow_steps(ctx, var_name, cluster_name, fn)
        self._expand_backward_reads(ctx, var_name, fn_id, cluster_name, fn)

    def _expand_backward_flow_steps(self, ctx: _ExpansionContext, var_name: str, cluster_name: str, fn: Any) -> None:
        for step in getattr(fn, "flow_steps", []):
            if len(ctx.graph.nodes) >= ctx.max_nodes:
                break
            if var_name not in step.target_expr and var_name != step.target_expr:
                continue
            is_src = any(sp.pattern in step.source_expr for sp in DEFAULT_TAINT_SOURCES)
            ctx.graph.add_node(
                node_id=step.source_expr,
                name=step.source_expr,
                kind=NodeKind.SYMBOL,
                cluster=cluster_name,
                location=step.location,
                is_source=is_src,
            )
            ctx.graph.add_edge(
                from_id=var_name,
                to_id=step.source_expr,
                kind=f"PRODUCED_BY_{step.step_kind.upper()}",
                location=step.location,
            )
            if step.source_expr != var_name and step.source_expr not in ctx.visited_vars:
                ctx.queue.append((step.source_expr, ctx.depth + 1))

    def _expand_backward_reads(
        self, ctx: _ExpansionContext, var_name: str, fn_id: str, cluster_name: str, fn: Any
    ) -> None:
        for r_var in fn.reads_variables:
            if len(ctx.graph.nodes) >= ctx.max_nodes:
                break
            ctx.graph.add_node(node_id=r_var, name=r_var, kind=NodeKind.SYMBOL, cluster=cluster_name)
            ctx.graph.add_edge(from_id=fn_id, to_id=r_var, kind="READS_FROM", location=fn.location)
            if r_var != var_name and r_var not in ctx.visited_vars:
                ctx.queue.append((r_var, ctx.depth + 1))

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
                dst_graph.nodes[node_id] = n
        for edge in src_graph.edges:
            if edge.from_id in keep_nodes and edge.to_id in keep_nodes:
                dst_graph.add_edge(edge.from_id, edge.to_id, edge.kind, edge.location)

    def _collect_model_variables(self, model: CodeModel, file_filter: str | None) -> dict[str, Any]:
        from pattern_detector.adapters.outbound.python_ast.py_parser_adapter import _PYTHON_BUILTINS_AND_KEYWORDS

        vars_map: dict[str, Any] = {}
        self._collect_state_variables(model, file_filter, _PYTHON_BUILTINS_AND_KEYWORDS, vars_map)
        self._collect_record_field_variables(model, file_filter, _PYTHON_BUILTINS_AND_KEYWORDS, vars_map)
        self._collect_function_io_variables(model, file_filter, _PYTHON_BUILTINS_AND_KEYWORDS, vars_map)
        return vars_map

    def _collect_state_variables(
        self, model: CodeModel, file_filter: str | None, builtins: frozenset[str], vars_map: dict[str, Any]
    ) -> None:
        for s in model.all_states():
            if self._is_valid_var(s.name, s.location, file_filter, builtins):
                vars_map[s.name] = s.location

    def _collect_record_field_variables(
        self, model: CodeModel, file_filter: str | None, builtins: frozenset[str], vars_map: dict[str, Any]
    ) -> None:
        for r in model.all_records():
            if file_filter and r.location and file_filter not in r.location.file_path:
                continue
            for f in r.fields:
                if f not in vars_map and self._is_valid_var(f, r.location, file_filter, builtins):
                    vars_map[f] = r.location

    def _collect_function_io_variables(
        self, model: CodeModel, file_filter: str | None, builtins: frozenset[str], vars_map: dict[str, Any]
    ) -> None:
        for fn in model.all_functions():
            if file_filter and fn.location and file_filter not in fn.location.file_path:
                continue
            for v in fn.reads_variables + fn.writes_variables + fn.modifies_variables:
                if v not in vars_map and self._is_valid_var(v, fn.location, file_filter, builtins):
                    vars_map[v] = fn.location

    def _is_valid_var(self, name: str, loc: Any, file_filter: str | None, builtins: frozenset[str]) -> bool:
        if not name or len(name) < 2 or name in builtins or not (name[0].isalpha() or name[0] == "_"):
            return False
        return not (file_filter and loc and file_filter not in loc.file_path)

    def _summarize_variable_flow(self, var_name: str, loc: Any, graph: DataFlowGraph) -> VariableFlowSummary:
        readers = [e.to_id.replace("fn_", "") for e in graph.edges if e.from_id == var_name and e.kind == "READS"]
        writers = [
            e.from_id.replace("fn_", "")
            for e in graph.edges
            if e.to_id == var_name and e.kind in ("WRITES", "MODIFIES")
        ]

        reach = len(graph.nodes) - 1
        impact = self._calculate_impact_level(reach, len(readers))

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

    def _calculate_impact_level(self, reach: int, readers_count: int) -> str:
        if reach >= 15 or readers_count >= 5:
            return "HIGH"
        if reach >= 4 or readers_count >= 2:
            return "MEDIUM"
        return "LOW"
