"""Interactive HTML Report Formatter for Data Flow Graphs (using Vis.js Network / Mermaid)."""

from __future__ import annotations

import html
import json
from typing import Any

from pattern_detector.domain.data_flow import (
    DataFlowGraph,
    DataFlowSummaryReport,
    NodeKind,
)


class DataFlowHtmlFormatter:
    """Formatter for generating interactive HTML visualizer for Data Flow graphs."""

    def format_single_graph(self, graph: DataFlowGraph, title: str = "") -> str:
        """Generate interactive HTML page for a single Data Flow Graph."""
        page_title = title or f"Data Flow {graph.direction.value}: {graph.root_id}"
        
        # Prepare graph data for Vis.js
        vis_data = self._prepare_vis_graph(graph)
        all_graphs_json = json.dumps({graph.root_id: vis_data})
        variables_summary_json = json.dumps([
            {
                "name": graph.root_id,
                "file_path": graph.nodes[graph.root_id].file_path if graph.root_id in graph.nodes else "",
                "line": graph.nodes[graph.root_id].line if graph.root_id in graph.nodes else 1,
                "readers": [e.to_id.replace("fn_", "") for e in graph.edges if e.from_id == graph.root_id and e.kind == "READS"],
                "writers": [e.from_id.replace("fn_", "") for e in graph.edges if e.to_id == graph.root_id and e.kind in ("WRITES", "MODIFIES")],
                "downstream_reach": len(graph.nodes) - 1,
                "max_depth": 3,
                "impact_level": "HIGH" if len(graph.nodes) > 4 else "MEDIUM",
            }
        ])

        return self._render_template(
            page_title=page_title,
            initial_root=graph.root_id,
            direction=graph.direction.value,
            all_graphs_json=all_graphs_json,
            variables_summary_json=variables_summary_json,
            total_variables=1,
            total_nodes=len(graph.nodes),
            total_edges=len(graph.edges),
        )

    def format_summary_report(self, report: DataFlowSummaryReport) -> str:
        """Generate interactive HTML dashboard for all variables in a codebase."""
        page_title = f"🌲 Data Flow Analysis Dashboard ({report.direction.value})"
        
        graphs_dict: dict[str, Any] = {}
        sorted_summaries = sorted(report.summaries, key=lambda x: (x.downstream_reach, len(x.readers)), reverse=True)
        for s in sorted_summaries[:100]:
            if s.graph:
                graphs_dict[s.name] = self._prepare_vis_graph(s.graph)

        initial_root = sorted_summaries[0].name if sorted_summaries else ""
        all_graphs_json = json.dumps(graphs_dict)
        variables_summary_json = json.dumps([
            {
                "name": s.name,
                "file_path": s.file_path,
                "line": s.line,
                "readers": s.readers,
                "writers": s.writers,
                "downstream_reach": s.downstream_reach,
                "max_depth": s.max_depth,
                "impact_level": s.impact_level,
            }
            for s in report.summaries
        ])

        total_nodes = sum(len(s.graph.nodes) for s in report.summaries if s.graph)
        total_edges = sum(len(s.graph.edges) for s in report.summaries if s.graph)

        return self._render_template(
            page_title=page_title,
            initial_root=initial_root,
            direction=report.direction.value,
            all_graphs_json=all_graphs_json,
            variables_summary_json=variables_summary_json,
            total_variables=report.total_variables,
            total_nodes=total_nodes,
            total_edges=total_edges,
        )

    def _prepare_vis_graph(self, graph: DataFlowGraph) -> dict[str, Any]:
        """Convert DataFlowGraph into Vis.js nodes and edges format."""
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        for node in graph.nodes.values():
            is_root = node.is_root or node.id == graph.root_id
            if node.kind == NodeKind.FUNCTION:
                shape = "box"
                color = {
                    "background": "#581c87",
                    "border": "#c084fc",
                    "highlight": {"background": "#7e22ce", "border": "#e9d5ff"},
                }
                font = {"color": "#f3e8ff", "face": "monospace", "size": 13, "bold": True}
                label = f"⚙️ {node.name}()"
            else:
                shape = "ellipse" if not is_root else "box"
                color = {
                    "background": "#0284c7" if is_root else "#0f172a",
                    "border": "#38bdf8" if is_root else "#0284c7",
                    "highlight": {"background": "#0369a1", "border": "#bae6fd"},
                }
                font = {"color": "#ffffff" if is_root else "#e0f2fe", "face": "monospace", "size": 14 if is_root else 12, "bold": is_root}
                label = f"🔷 {node.name}" if not is_root else f"⭐ {node.name} (ROOT)"

            nodes.append({
                "id": node.id,
                "label": label,
                "shape": shape,
                "color": color,
                "font": font,
                "margin": 10,
                "borderWidth": 3 if is_root else 2,
                "shadow": is_root,
                "title": f"<b>{node.name}</b><br>Kind: {node.kind.value}<br>Cluster: {node.cluster}<br>{node.file_path}:{node.line}",
            })

        for i, edge in enumerate(graph.edges):
            kind_lower = edge.kind.lower()
            edge_color = "#38bdf8" if kind_lower == "reads" else ("#f43f5e" if "write" in kind_lower else "#fbbf24")
            dashes = "modifi" in kind_lower

            edges.append({
                "id": f"e_{i}",
                "from": edge.from_id,
                "to": edge.to_id,
                "label": f" {kind_lower} ",
                "arrows": "to",
                "color": {"color": edge_color, "highlight": "#ffffff"},
                "font": {"color": edge_color, "size": 10, "face": "monospace", "align": "top"},
                "dashes": dashes,
                "smooth": {"type": "cubicBezier", "roundness": 0.2},
            })

        return {"nodes": nodes, "edges": edges}

    def _render_template(
        self,
        page_title: str,
        initial_root: str,
        direction: str,
        all_graphs_json: str,
        variables_summary_json: str,
        total_variables: int,
        total_nodes: int,
        total_edges: int,
    ) -> str:
        """Render complete standalone HTML template with embedded JavaScript and CSS."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(page_title)} - DPX-Cpp Data Flow</title>
    <!-- Vis.js Network CDN -->
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        :root {{
            --bg-primary: #090d16;
            --bg-secondary: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #334155;
            --border: #334155;
            --border-highlight: #38bdf8;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent-cyan: #38bdf8;
            --accent-purple: #c084fc;
            --accent-emerald: #34d399;
            --accent-rose: #f43f5e;
            --accent-amber: #fbbf24;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }}
        /* Header */
        header {{
            background: linear-gradient(135deg, #0b1329 0%, #1e1b4b 100%);
            border-bottom: 1px solid var(--border);
            padding: 12px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 10;
        }}
        .logo-area {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .logo-badge {{
            background: linear-gradient(135deg, #0284c7, #9333ea);
            color: #fff;
            padding: 6px 12px;
            border-radius: 8px;
            font-weight: 800;
            font-size: 14px;
            letter-spacing: 0.5px;
        }}
        .title {{
            font-size: 18px;
            font-weight: 700;
            color: var(--text-primary);
        }}
        .direction-pill {{
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 700;
            background: #0284c722;
            color: var(--accent-cyan);
            border: 1px solid var(--accent-cyan);
        }}
        .stats-bar {{
            display: flex;
            gap: 16px;
            font-size: 13px;
        }}
        .stat-item {{
            background: var(--bg-secondary);
            padding: 4px 12px;
            border-radius: 6px;
            border: 1px solid var(--border);
            display: flex;
            gap: 6px;
        }}
        .stat-val {{
            font-weight: 700;
            color: var(--accent-cyan);
        }}

        /* Main Workspace Layout */
        .workspace {{
            display: flex;
            flex: 1;
            overflow: hidden;
        }}

        /* Left Sidebar: Variable List */
        .sidebar {{
            width: 380px;
            background-color: var(--bg-secondary);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        .sidebar-header {{
            padding: 14px;
            border-bottom: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .search-box {{
            width: 100%;
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 13px;
            outline: none;
        }}
        .search-box:focus {{
            border-color: var(--accent-cyan);
        }}
        .filter-tabs {{
            display: flex;
            gap: 6px;
            overflow-x: auto;
        }}
        .filter-tab {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            font-size: 11px;
            font-weight: 600;
            padding: 4px 8px;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.15s ease;
        }}
        .filter-tab.active, .filter-tab:hover {{
            background: #0284c733;
            color: var(--accent-cyan);
            border-color: var(--accent-cyan);
        }}
        .var-list {{
            flex: 1;
            overflow-y: auto;
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        .var-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px 12px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        .var-card:hover {{
            background: var(--bg-card-hover);
            border-color: var(--accent-cyan);
            transform: translateX(2px);
        }}
        .var-card.selected {{
            background: #0c4a6e44;
            border-color: var(--accent-cyan);
            box-shadow: 0 0 12px rgba(56, 189, 248, 0.2);
        }}
        .var-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .var-name {{
            font-family: monospace;
            font-weight: 700;
            font-size: 14px;
            color: var(--text-primary);
        }}
        .impact-badge {{
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
        }}
        .impact-CRITICAL {{ background: #881337; color: #fecdd3; border: 1px solid #f43f5e; }}
        .impact-HIGH {{ background: #78350f; color: #fde68a; border: 1px solid #fbbf24; }}
        .impact-MEDIUM {{ background: #164e63; color: #a5f3fc; border: 1px solid #22d3ee; }}
        .impact-LOW {{ background: #334155; color: #cbd5e1; border: 1px solid #64748b; }}

        .var-card-meta {{
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            color: var(--text-muted);
        }}
        .meta-tags {{
            display: flex;
            gap: 8px;
        }}
        .meta-tag {{
            color: var(--accent-purple);
            font-weight: 600;
        }}

        /* Center Canvas: Interactive Vis.js Network */
        .canvas-container {{
            flex: 1;
            position: relative;
            background: radial-gradient(circle at center, #111827 0%, #090d16 100%);
            display: flex;
            flex-direction: column;
        }}
        #network {{
            flex: 1;
            width: 100%;
            height: 100%;
        }}
        .canvas-toolbar {{
            position: absolute;
            top: 14px;
            right: 14px;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border);
            padding: 6px;
            border-radius: 8px;
            display: flex;
            gap: 6px;
            z-index: 10;
        }}
        .btn {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }}
        .btn:hover {{
            background: #0284c7;
            border-color: var(--accent-cyan);
        }}
        .btn.active {{
            background: #0284c7;
            border-color: var(--accent-cyan);
        }}

        /* Legend Panel */
        .legend {{
            position: absolute;
            bottom: 14px;
            left: 14px;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border);
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 12px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            z-index: 10;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 3px;
        }}

        /* Drawer / Details Bottom Panel */
        .details-panel {{
            height: 160px;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border);
            padding: 14px 20px;
            overflow-y: auto;
            display: flex;
            gap: 24px;
        }}
        .detail-block {{
            flex: 1;
        }}
        .detail-title {{
            font-size: 12px;
            font-weight: 700;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }}
        .detail-content {{
            font-size: 13px;
            color: var(--text-primary);
            line-height: 1.5;
        }}
        .code-pill {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            color: var(--accent-cyan);
            display: inline-block;
            margin: 2px;
        }}
    </style>
</head>
<body>
    <header>
        <div class="logo-area">
            <span class="logo-badge">DPX-Cpp</span>
            <span class="title">{html.escape(page_title)}</span>
            <span class="direction-pill">Direction: {direction}</span>
        </div>
        <div class="stats-bar">
            <div class="stat-item">Variables: <span class="stat-val">{total_variables}</span></div>
            <div class="stat-item">Graph Nodes: <span class="stat-val">{total_nodes}</span></div>
            <div class="stat-item">Data Flow Edges: <span class="stat-val">{total_edges}</span></div>
        </div>
    </header>

    <div class="workspace">
        <!-- Sidebar: Variables Matrix -->
        <aside class="sidebar">
            <div class="sidebar-header">
                <input type="text" id="searchInput" class="search-box" placeholder="🔍 Search variables, fields...">
                <div class="filter-tabs">
                    <button class="filter-tab active" onclick="filterImpact('ALL')">All</button>
                    <button class="filter-tab" onclick="filterImpact('CRITICAL')">Critical</button>
                    <button class="filter-tab" onclick="filterImpact('HIGH')">High</button>
                    <button class="filter-tab" onclick="filterImpact('MEDIUM')">Medium</button>
                    <button class="filter-tab" onclick="filterImpact('LOW')">Low</button>
                </div>
            </div>
            <div class="var-list" id="varList"></div>
        </aside>

        <!-- Canvas Container -->
        <main class="canvas-container">
            <div class="canvas-toolbar">
                <button class="btn active" id="layoutHierarchicalBtn" onclick="setLayout('hierarchical')">🌳 Tree View</button>
                <button class="btn" id="layoutPhysicsBtn" onclick="setLayout('physics')">⚛️ Force Graph</button>
                <button class="btn" onclick="network.fit()">🔍 Fit</button>
                <button class="btn" onclick="exportJSON()">💾 Export JSON</button>
            </div>

            <div id="network"></div>

            <div class="legend">
                <div class="legend-item"><div class="legend-color" style="background:#0284c7;border:1px solid #38bdf8;"></div> Selected Root Variable</div>
                <div class="legend-item"><div class="legend-color" style="background:#581c87;border:1px solid #c084fc;"></div> Function (Reader / Writer)</div>
                <div class="legend-item"><div class="legend-color" style="background:#0f172a;border:1px solid #0284c7;"></div> Downstream Variable / State</div>
                <div class="legend-item"><div class="legend-color" style="background:#38bdf8;"></div> Reads Edge</div>
                <div class="legend-item"><div class="legend-color" style="background:#f43f5e;"></div> Writes / Modifies Edge</div>
            </div>
        </main>
    </div>

    <!-- Details Panel -->
    <div class="details-panel" id="detailsPanel">
        <div class="detail-block">
            <div class="detail-title">Selected Variable Details</div>
            <div class="detail-content" id="detailRootMeta">Select a variable to inspect full propagation metrics.</div>
        </div>
        <div class="detail-block">
            <div class="detail-title">Direct Function Readers</div>
            <div class="detail-content" id="detailReaders">-</div>
        </div>
        <div class="detail-block">
            <div class="detail-title">Direct Function Writers / Modifiers</div>
            <div class="detail-content" id="detailWriters">-</div>
        </div>
    </div>

    <script>
        const allGraphs = {all_graphs_json};
        const variablesSummary = {variables_summary_json};
        let currentRoot = "{initial_root}";
        let currentLayout = "hierarchical";
        let network = null;
        let activeImpactFilter = "ALL";

        function renderVariableList() {{
            const container = document.getElementById("varList");
            const query = document.getElementById("searchInput").value.toLowerCase();
            container.innerHTML = "";

            variablesSummary.forEach(v => {{
                if (activeImpactFilter !== "ALL" && v.impact_level !== activeImpactFilter) return;
                if (query && !v.name.toLowerCase().includes(query) && !v.file_path.toLowerCase().includes(query)) return;

                const card = document.createElement("div");
                card.className = `var-card ${{v.name === currentRoot ? 'selected' : ''}}`;
                card.onclick = () => selectVariable(v.name);

                const fileName = v.file_path ? v.file_path.split("/").pop() + ":" + v.line : "global";

                card.innerHTML = `
                    <div class="var-card-header">
                        <span class="var-name">🔷 ${{v.name}}</span>
                        <span class="impact-badge impact-${{v.impact_level}}">${{v.impact_level}}</span>
                    </div>
                    <div class="var-card-meta">
                        <span>${{fileName}}</span>
                        <div class="meta-tags">
                            <span class="meta-tag">Reach: ${{v.downstream_reach}}</span>
                            <span class="meta-tag">Depth: ${{v.max_depth}}</span>
                        </div>
                    </div>
                `;
                container.appendChild(card);
            }});
        }}

        function filterImpact(impact) {{
            activeImpactFilter = impact;
            document.querySelectorAll(".filter-tab").forEach(tab => {{
                tab.classList.toggle("active", tab.innerText.toUpperCase() === impact);
            }});
            renderVariableList();
        }}

        document.getElementById("searchInput").addEventListener("input", renderVariableList);

        function selectVariable(name) {{
            currentRoot = name;
            renderVariableList();
            renderNetwork(name);
            updateDetails(name);
        }}

        function updateDetails(name) {{
            const v = variablesSummary.find(item => item.name === name);
            if (!v) return;

            document.getElementById("detailRootMeta").innerHTML = `
                <b>${{v.name}}</b> (Defined at <span class="code-pill">${{v.file_path || "global"}}:${{v.line}}</span>)<br>
                Impact: <span class="impact-badge impact-${{v.impact_level}}">${{v.impact_level}}</span> | Downstream Reach: <b>${{v.downstream_reach}} nodes</b> | Max Depth: <b>${{v.max_depth}}</b>
            `;

            const readersElem = document.getElementById("detailReaders");
            if (v.readers && v.readers.length > 0) {{
                readersElem.innerHTML = v.readers.map(r => `<span class="code-pill">⚙️ ${{r}}()</span>`).join(" ");
            }} else {{
                readersElem.innerHTML = '<span style="color:var(--text-muted)">None (Not directly read)</span>';
            }}

            const writersElem = document.getElementById("detailWriters");
            if (v.writers && v.writers.length > 0) {{
                writersElem.innerHTML = v.writers.map(w => `<span class="code-pill">⚙️ ${{w}}()</span>`).join(" ");
            }} else {{
                writersElem.innerHTML = '<span style="color:var(--text-muted)">None (Read-only or Extern)</span>';
            }}
        }}

        function renderNetwork(varName) {{
            const graphData = allGraphs[varName];
            const container = document.getElementById("network");
            if (!graphData) {{
                container.innerHTML = `<div style="display:flex;justify-content:center;align-items:center;height:100%;color:var(--text-muted)">No propagation data found for ${{varName}}.</div>`;
                return;
            }}

            const data = {{
                nodes: new vis.DataSet(graphData.nodes),
                edges: new vis.DataSet(graphData.edges)
            }};

            const options = {{
                layout: currentLayout === "hierarchical" ? {{
                    hierarchical: {{
                        direction: "LR",
                        sortMethod: "directed",
                        levelSeparation: 180,
                        nodeSpacing: 100,
                    }}
                }} : {{
                    improvedLayout: true
                }},
                physics: currentLayout === "physics" ? {{
                    solver: "forceAtlas2Based",
                    forceAtlas2Based: {{
                        gravitationalConstant: -50,
                        centralGravity: 0.01,
                        springLength: 100,
                        springConstant: 0.08
                    }}
                }} : false,
                nodes: {{
                    borderWidth: 2,
                    shadow: true
                }},
                edges: {{
                    width: 2,
                    shadow: true
                }},
                interaction: {{
                    hover: true,
                    tooltipDelay: 100,
                    zoomView: true,
                    dragView: true
                }}
            }};

            if (network) network.destroy();
            network = new vis.Network(container, data, options);
        }}

        function setLayout(layoutType) {{
            currentLayout = layoutType;
            document.getElementById("layoutHierarchicalBtn").classList.toggle("active", layoutType === "hierarchical");
            document.getElementById("layoutPhysicsBtn").classList.toggle("active", layoutType === "physics");
            if (currentRoot) renderNetwork(currentRoot);
        }}

        function exportJSON() {{
            const v = variablesSummary.find(item => item.name === currentRoot);
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(allGraphs[currentRoot] || {{}}, null, 2));
            const downloadAnchor = document.createElement('a');
            downloadAnchor.setAttribute("href", dataStr);
            downloadAnchor.setAttribute("download", `dataflow_${{currentRoot}}.json`);
            document.body.appendChild(downloadAnchor);
            downloadAnchor.click();
            downloadAnchor.remove();
        }}

        // Initialize UI on load
        window.addEventListener("DOMContentLoaded", () => {{
            renderVariableList();
            if (currentRoot) selectVariable(currentRoot);
        }});
    </script>
</body>
</html>
"""
