"""Token-Efficient LLM / AI Prompt Context Formatter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pattern_detector.domain.data_flow import DataFlowGraph, DataFlowSummaryReport
from pattern_detector.domain.detection import DetectionReport
from pattern_detector.domain.insights import InsightsReport
from pattern_detector.domain.value_objects import PatternCategory


@dataclass
class _TraversalContext:
    adj: dict[str, list[tuple[str, str]]]
    out_paths: list[list[str]]


class LlmReportFormatter:
    """Formatter that generates clean, token-efficient architectural context for LLMs."""

    def format_scan_report(
        self,
        report: DetectionReport,
        insights_report: InsightsReport | None = None,
    ) -> str:
        """Render DetectionReport as structured XML/Markdown context for LLMs."""
        project_path = report.project_path or "."
        lines = [
            "<codebase_architecture_analysis>",
            f'  <project path="{project_path}" files="{report.scanned_files_count}" detections="{report.total_detections_count}">',
        ]
        lines.extend(self._render_category_summary(report.summary_by_category))

        patterns, adherences, violations = self._partition_detections(report.detections)
        self._append_detection_sections(lines, patterns, adherences, violations, insights_report)

        lines.extend(["  </project>", "</codebase_architecture_analysis>"])
        return "\n".join(lines)

    def _partition_detections(self, detections: list[Any]) -> tuple[list[Any], list[Any], list[Any]]:
        patterns: list[Any] = []
        adherences: list[Any] = []
        violations: list[Any] = []
        for d in detections:
            if d.pattern_category != PatternCategory.PRINCIPLE:
                patterns.append(d)
            elif "Adherence" in d.summary or "adherence" in d.target_kind:
                adherences.append(d)
            else:
                violations.append(d)
        return patterns, adherences, violations

    def _append_detection_sections(
        self,
        lines: list[str],
        patterns: list[Any],
        adherences: list[Any],
        violations: list[Any],
        insights_report: InsightsReport | None,
    ) -> None:
        if patterns:
            lines.extend(self._render_design_patterns(patterns))
        if adherences:
            lines.extend(self._render_solid_adherences(adherences))
        if violations:
            lines.extend(self._render_architectural_violations(violations))
        if insights_report and insights_report.insights:
            lines.extend(self._render_pattern_data_insights(insights_report))

    def _render_category_summary(self, summary_by_category: dict[str, int]) -> list[str]:
        lines = ["    <category_summary>"]
        for cat, count in summary_by_category.items():
            if count > 0:
                lines.append(f'      <category name="{cat.upper()}" count="{count}" />')
        lines.append("    </category_summary>")
        return lines

    def _render_design_patterns(self, patterns: list[Any]) -> list[str]:
        lines = ["    <design_patterns>"]
        for d in patterns:
            loc = f"{d.primary_location.file_path}:{d.primary_location.line}" if d.primary_location else ""
            lines.append(
                f'      <pattern type="{d.pattern_type.value}" target="{d.target_name}" confidence="{d.confidence.percentage_str}" location="{loc}">'
            )
            lines.append(f"        <summary>{d.summary}</summary>")
            lines.append("        <evidence>")
            for ev in d.evidences:
                lines.append(
                    f'          <item rule="{ev.rule_code}" weight="+{int(ev.weight * 100)}%">{ev.description}</item>'
                )
            lines.append("        </evidence>")
            lines.append("      </pattern>")
        lines.append("    </design_patterns>")
        return lines

    def _render_solid_adherences(self, adherences: list[Any]) -> list[str]:
        lines = ["    <solid_and_architectural_adherences>"]
        for a in adherences:
            loc = f"{a.primary_location.file_path}:{a.primary_location.line}" if a.primary_location else ""
            lines.append(
                f'      <adherence rule="{a.pattern_type.value}" target="{a.target_name}" confidence="{a.confidence.percentage_str}" location="{loc}">'
            )
            lines.append(f"        <summary>{a.summary}</summary>")
            lines.append("        <evidence>")
            for ev in a.evidences:
                lines.append(f'          <item rule="{ev.rule_code}">{ev.description}</item>')
            lines.append("        </evidence>")
            lines.append("      </adherence>")
        lines.append("    </solid_and_architectural_adherences>")
        return lines

    def _render_architectural_violations(self, violations: list[Any]) -> list[str]:
        lines = ["    <architectural_violations_and_risks>"]
        for v in violations:
            loc = f"{v.primary_location.file_path}:{v.primary_location.line}" if v.primary_location else ""
            lines.append(
                f'      <violation rule="{v.pattern_type.value}" target="{v.target_name}" confidence="{v.confidence.percentage_str}" location="{loc}">'
            )
            lines.append(f"        <risk>{v.summary}</risk>")
            lines.append("        <evidence>")
            for ev in v.evidences:
                lines.append(f'          <item rule="{ev.rule_code}">{ev.description}</item>')
            lines.append("        </evidence>")
            lines.append("      </violation>")
        lines.append("    </architectural_violations_and_risks>")
        return lines

    def _render_pattern_data_insights(self, insights_report: InsightsReport) -> list[str]:
        lines = ["    <pattern_data_insights>"]
        for ins in insights_report.insights:
            loc = f"{ins.location.file_path}:{ins.location.line}" if ins.location else ""
            lines.append(
                f'      <insight pattern="{ins.target_pattern.value}" target="{ins.target_name}" severity="{ins.severity.value}" category="{ins.category.value}" location="{loc}">'
            )
            lines.append(f"        <title>{ins.title}</title>")
            lines.append(f"        <data_entity>{ins.data_entity}</data_entity>")
            lines.append(f"        <description>{ins.description}</description>")
            lines.append(f"        <suggestion>{ins.suggestion}</suggestion>")
            if ins.code_snippet:
                lines.append(f"        <recommended_code><![CDATA[\n{ins.code_snippet}\n]]></recommended_code>")
            lines.append("      </insight>")
        lines.append("    </pattern_data_insights>")
        return lines

    def format_data_flow_graph(self, graph: DataFlowGraph) -> str:
        """Render single DataFlowGraph as token-dense propagation paths for LLMs."""
        reads_by, writes_by = self._collect_direct_root_interactions(graph)
        lines: list[str] = [
            f'<data_flow_analysis direction="{graph.direction.value}" root_variable="{graph.root_id}">',
            f'  <summary nodes="{len(graph.nodes)}" edges="{len(graph.edges)}">',
            f'    <direct_readers count="{len(reads_by)}">{", ".join(reads_by) if reads_by else "none"}</direct_readers>',
            f'    <direct_writers count="{len(writes_by)}">{", ".join(writes_by) if writes_by else "none"}</direct_writers>',
            "  </summary>",
        ]

        rendered_paths = self._extract_propagation_paths(graph)
        lines.append("  <propagation_paths>")
        for p_str in rendered_paths:
            lines.append(f"    <path>{p_str}</path>")
        lines.append("  </propagation_paths>")
        lines.append("</data_flow_analysis>")
        return "\n".join(lines)

    def _collect_direct_root_interactions(self, graph: DataFlowGraph) -> tuple[list[str], list[str]]:
        reads_by = [e.to_id.replace("fn_", "") for e in graph.edges if e.from_id == graph.root_id and e.kind == "READS"]
        writes_by = [
            e.from_id.replace("fn_", "")
            for e in graph.edges
            if e.to_id == graph.root_id and e.kind in ("WRITES", "MODIFIES")
        ]
        return reads_by, writes_by

    def _extract_propagation_paths(self, graph: DataFlowGraph) -> list[str]:
        adj = self._build_adjacency_map(graph.edges)
        paths: list[list[str]] = []
        ctx = _TraversalContext(adj=adj, out_paths=paths)
        self._dfs_traverse(ctx, graph.root_id, [graph.root_id], {graph.root_id}, 0)
        return self._deduplicate_and_render_paths(paths)

    def _build_adjacency_map(self, edges: list[Any]) -> dict[str, list[tuple[str, str]]]:
        adj: dict[str, list[tuple[str, str]]] = {}
        for edge in edges:
            adj.setdefault(edge.from_id, []).append((edge.to_id, edge.kind))
        return adj

    def _dfs_traverse(
        self,
        ctx: _TraversalContext,
        current: str,
        current_path: list[str],
        visited: set[str],
        depth: int,
    ) -> None:
        if depth > 10:
            ctx.out_paths.append(current_path)
            return

        neighbors = ctx.adj.get(current, [])
        if not neighbors:
            if len(current_path) > 1:
                ctx.out_paths.append(current_path)
            return

        for nxt, kind in neighbors:
            clean_name = nxt.replace("fn_", "") + ("()" if "fn_" in nxt else "")
            step_str = f"-[{kind.lower()}]-> {clean_name}"
            if nxt not in visited:
                self._dfs_traverse(ctx, nxt, current_path + [step_str], visited | {nxt}, depth + 1)
            else:
                ctx.out_paths.append(current_path + [step_str + " (cycle)"])

    def _deduplicate_and_render_paths(self, paths: list[list[str]]) -> list[str]:
        seen_paths: set[str] = set()
        rendered: list[str] = []
        for p in paths[:25]:
            p_str = " ".join(p)
            if p_str not in seen_paths:
                seen_paths.add(p_str)
                rendered.append(p_str)
        return rendered

    def format_data_flow_summary(self, report: DataFlowSummaryReport) -> str:
        """Render multi-variable DataFlowSummaryReport for LLM context."""
        lines: list[str] = [
            f'<data_flow_project_summary target="{report.target_path}" direction="{report.direction.value}" total_variables="{report.total_variables}">',
        ]

        for s in sorted(report.summaries, key=lambda x: (x.downstream_reach, len(x.readers)), reverse=True):
            loc_str = f"{s.file_path}:{s.line}" if s.file_path else "global"
            lines.append(
                f'  <variable name="{s.name}" impact="{s.impact_level}" reach_nodes="{s.downstream_reach}" max_depth="{s.max_depth}" location="{loc_str}">'
            )
            lines.append(f'    <readers count="{len(s.readers)}">{", ".join(s.readers)}</readers>')
            lines.append(f'    <writers count="{len(s.writers)}">{", ".join(s.writers)}</writers>')
            lines.append("  </variable>")

        lines.append("</data_flow_project_summary>")
        return "\n".join(lines)
