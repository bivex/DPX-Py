"""Interactive HTML Report Formatter for Data Flow Graphs (using Cytoscape.js & Semantic UI / Fomantic-UI)."""

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
    """Formatter for generating high-performance interactive HTML visualizer for Data Flow graphs using Cytoscape.js and Semantic UI."""

    def format_single_graph(self, graph: DataFlowGraph, title: str = "") -> str:
        """Generate interactive HTML page for a single Data Flow Graph."""
        page_title = title or f"Data Flow {graph.direction.value}: {graph.root_id}"

        # Prepare graph data for Cytoscape.js
        cy_elements = self._prepare_cytoscape_elements(graph)
        all_graphs_json = json.dumps({graph.root_id: cy_elements})
        variables_summary_json = json.dumps(
            [
                {
                    "name": graph.root_id,
                    "file_path": graph.nodes[graph.root_id].file_path if graph.root_id in graph.nodes else "",
                    "line": graph.nodes[graph.root_id].line if graph.root_id in graph.nodes else 1,
                    "readers": [
                        e.to_id.replace("fn_", "")
                        for e in graph.edges
                        if e.from_id == graph.root_id and e.kind == "READS"
                    ],
                    "writers": [
                        e.from_id.replace("fn_", "")
                        for e in graph.edges
                        if e.to_id == graph.root_id and e.kind in ("WRITES", "MODIFIES")
                    ],
                    "downstream_reach": len(graph.nodes) - 1,
                    "max_depth": 3,
                    "impact_level": "HIGH" if len(graph.nodes) > 4 else "MEDIUM",
                }
            ]
        )

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
        for s in sorted_summaries[:40]:
            if s.graph:
                graphs_dict[s.name] = self._prepare_cytoscape_elements(s.graph)

        initial_root = sorted_summaries[0].name if sorted_summaries else ""
        all_graphs_json = json.dumps(graphs_dict)
        variables_summary_json = json.dumps(
            [
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
            ]
        )

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

    def _prepare_cytoscape_elements(self, graph: DataFlowGraph) -> list[dict[str, Any]]:
        """Convert DataFlowGraph into high-performance Cytoscape.js elements."""
        elements: list[dict[str, Any]] = []

        for node in graph.nodes.values():
            is_root = node.is_root or node.id == graph.root_id
            if node.kind == NodeKind.FUNCTION:
                shape = "round-rectangle"
                bg_color = "#581c87"
                border_color = "#c084fc"
                text_color = "#f3e8ff"
                label = f"⚙️ {node.name}()"
                node_type = "function"
            else:
                node_type = "variable"
                if is_root:
                    shape = "round-rectangle"
                    bg_color = "#0284c7"
                    border_color = "#38bdf8"
                    text_color = "#ffffff"
                    label = f"⭐ {node.name}"
                else:
                    shape = "ellipse"
                    bg_color = "#0f172a"
                    border_color = "#0284c7"
                    text_color = "#e0f2fe"
                    label = f"🔷 {node.name}"

            elements.append(
                {
                    "group": "nodes",
                    "data": {
                        "id": node.id,
                        "label": label,
                        "name": node.name,
                        "kind": node.kind.value,
                        "node_type": node_type,
                        "is_root": is_root,
                        "file_path": node.file_path,
                        "line": node.line,
                        "cluster": node.cluster,
                        "shape": shape,
                        "bgColor": bg_color,
                        "borderColor": border_color,
                        "textColor": text_color,
                        "borderWidth": 3 if is_root else 2,
                    },
                }
            )

        for i, edge in enumerate(graph.edges):
            kind_lower = edge.kind.lower()
            edge_color = "#38bdf8" if kind_lower == "reads" else ("#f43f5e" if "write" in kind_lower else "#fbbf24")
            line_style = "dashed" if "modifi" in kind_lower else "solid"

            elements.append(
                {
                    "group": "edges",
                    "data": {
                        "id": f"e_{i}_{edge.from_id}_{edge.to_id}",
                        "source": edge.from_id,
                        "target": edge.to_id,
                        "label": f" {kind_lower} ",
                        "kind": edge.kind,
                        "color": edge_color,
                        "lineStyle": line_style,
                    },
                }
            )

        return elements

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
        """Render complete standalone HTML template with Cytoscape.js and Semantic UI."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(page_title)} - DPX-Py Data Flow</title>
    <!-- Fomantic-UI (Semantic UI) CSS -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/fomantic-ui@2.9.3/dist/semantic.min.css">
    <!-- Cytoscape.js Core & Layout Engines -->
    <script src="https://cdn.jsdelivr.net/npm/jquery@3.7.1/dist/jquery.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/fomantic-ui@2.9.3/dist/semantic.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.30.2/cytoscape.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/dagre/0.8.5/dagre.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/cytoscape-dagre@2.5.0/cytoscape-dagre.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/webcola/3.4.0/cola.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/cytoscape-cola@2.5.1/cytoscape-cola.min.js"></script>

    <style>
        :root {{
            --bg-page: #090d16;
            --bg-sidebar: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #334155;
            --border-color: #334155;
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
            background-color: var(--bg-page) !important;
            color: #f8fafc !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}

        /* Semantic UI Customizations for Dark Mode */
        .ui.inverted.menu {{
            background: linear-gradient(135deg, #0b1329 0%, #1e1b4b 100%) !important;
            border-bottom: 1px solid #1e293b !important;
            margin: 0 !important;
            border-radius: 0 !important;
        }}
        .ui.inverted.segment {{
            background: var(--bg-sidebar) !important;
            border: 1px solid var(--border-color) !important;
        }}

        /* Workspace Grid */
        .app-workspace {{
            display: flex;
            flex: 1;
            overflow: hidden;
            height: calc(100vh - 55px - 140px);
        }}

        /* Sidebar */
        .app-sidebar {{
            width: 380px;
            background: var(--bg-sidebar);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
        }}
        .sidebar-header-box {{
            padding: 12px;
            background: #0b1120;
            border-bottom: 1px solid var(--border-color);
        }}
        .var-list-container {{
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}

        /* Variable Card */
        .var-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 10px 12px;
            cursor: pointer;
            transition: all 0.15s ease-in-out;
            display: flex;
            flex-direction: column;
            gap: 5px;
        }}
        .var-card:hover {{
            background: var(--bg-card-hover);
            border-color: var(--accent-cyan);
            transform: translateX(2px);
        }}
        .var-card.active {{
            background: #0c4a6e44 !important;
            border-color: var(--accent-cyan) !important;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.25);
        }}
        .var-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .var-name-text {{
            font-family: monospace;
            font-weight: 700;
            font-size: 13px;
            color: #f8fafc;
            word-break: break-all;
        }}
        .var-card-meta {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11px;
            color: #94a3b8;
        }}

        /* Canvas Area */
        .app-canvas-container {{
            flex: 1;
            position: relative;
            background: #060911;
            overflow: hidden;
        }}
        #cy {{
            width: 100%;
            height: 100%;
            display: block;
        }}

        /* Floating Toolbar */
        .canvas-toolbar {{
            position: absolute;
            top: 14px;
            right: 16px;
            z-index: 100;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 6px 10px;
            display: flex;
            align-items: center;
            gap: 6px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
        }}

        /* Floating Legend */
        .canvas-legend {{
            position: absolute;
            bottom: 14px;
            left: 16px;
            z-index: 100;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 8px 12px;
            display: flex;
            gap: 12px;
            font-size: 11px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
        }}
        .legend-badge {{
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 2px;
            margin-right: 4px;
            vertical-align: middle;
        }}

        /* Bottom Inspector */
        .app-inspector {{
            height: 140px;
            background: #0b1120;
            border-top: 1px solid var(--border-color);
            padding: 12px 20px;
            overflow-y: auto;
            display: flex;
            gap: 20px;
        }}
        .inspector-col {{
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .inspector-title {{
            font-size: 11px;
            font-weight: 700;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .inspector-body {{
            font-size: 13px;
            color: #f8fafc;
            line-height: 1.4;
        }}
        .code-tag {{
            background: #1e293b;
            border: 1px solid #334155;
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

    <!-- Semantic UI Inverted Menu Header -->
    <div class="ui inverted borderless menu">
        <div class="header item">
            <i class="project diagram icon" style="color: #38bdf8;"></i>
            <span style="font-weight: 700; font-size: 15px; margin-left: 6px;">DPX-Py Data Flow Engine</span>
        </div>
        <div class="item">
            <span class="ui mini teal label"><i class="compass icon"></i> Direction: {direction}</span>
            <span class="ui mini blue label"><i class="bolt icon"></i> Cytoscape.js Turbo</span>
        </div>
        <div class="right menu">
            <div class="item">
                <div class="ui mini inverted statistics" style="margin: 0;">
                    <div class="statistic" style="margin: 0 10px;">
                        <div class="value" style="color: #38bdf8;">{total_variables}</div>
                        <div class="label" style="color: #94a3b8; font-size: 8px;">Variables</div>
                    </div>
                    <div class="statistic" style="margin: 0 10px;">
                        <div class="value" style="color: #c084fc;">{total_nodes}</div>
                        <div class="label" style="color: #94a3b8; font-size: 8px;">Nodes</div>
                    </div>
                    <div class="statistic" style="margin: 0 10px;">
                        <div class="value" style="color: #34d399;">{total_edges}</div>
                        <div class="label" style="color: #94a3b8; font-size: 8px;">Edges</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Workspace: Sidebar + Canvas -->
    <div class="app-workspace">
        
        <!-- Sidebar -->
        <aside class="app-sidebar">
            <div class="sidebar-header-box">
                <div class="ui fluid mini icon inverted input">
                    <input type="text" id="searchInput" placeholder="Search variable or module...">
                    <i class="search icon"></i>
                </div>
                <div class="ui mini inverted secondary pointing menu" style="margin-top: 8px; margin-bottom: 0;">
                    <a class="active item" onclick="filterImpact('ALL')">All</a>
                    <a class="item" onclick="filterImpact('CRITICAL')">Critical</a>
                    <a class="item" onclick="filterImpact('HIGH')">High</a>
                    <a class="item" onclick="filterImpact('MEDIUM')">Medium</a>
                    <a class="item" onclick="filterImpact('LOW')">Low</a>
                </div>
            </div>
            <div class="var-list-container" id="varList"></div>
        </aside>

        <!-- Main Canvas -->
        <main class="app-canvas-container">
            
            <!-- Semantic UI Canvas Toolbar -->
            <div class="canvas-toolbar">
                <div class="ui mini inverted buttons">
                    <button class="ui active blue button" id="btnLayoutDagre" onclick="applyLayout('dagre')"><i class="sitemap icon"></i> Hierarchy</button>
                    <button class="ui purple button" id="btnLayoutCola" onclick="applyLayout('cola')"><i class="atom icon"></i> Force</button>
                    <button class="ui teal button" id="btnLayoutBreadth" onclick="applyLayout('breadthfirst')"><i class="tree icon"></i> Tree</button>
                    <button class="ui grey button" id="btnLayoutConcentric" onclick="applyLayout('concentric')"><i class="circle notch icon"></i> Orbit</button>
                </div>
                <div class="ui mini inverted icon buttons" style="margin-left: 6px;">
                    <button class="ui button" title="Fit to Screen" onclick="cy.fit(undefined, 30)"><i class="expand icon"></i></button>
                    <button class="ui button" title="Center View" onclick="cy.center()"><i class="crosshairs icon"></i></button>
                    <button class="ui button" title="Download PNG" onclick="exportPNG()"><i class="camera icon"></i></button>
                    <button class="ui button" title="Export JSON" onclick="exportJSON()"><i class="download icon"></i></button>
                </div>
            </div>

            <!-- Cytoscape High Performance Canvas -->
            <div id="cy"></div>

            <!-- Legend -->
            <div class="canvas-legend">
                <div><span class="legend-badge" style="background:#0284c7; border: 1px solid #38bdf8;"></span> Root Target</div>
                <div><span class="legend-badge" style="background:#581c87; border: 1px solid #c084fc;"></span> Function (Reader/Writer)</div>
                <div><span class="legend-badge" style="background:#0f172a; border: 1px solid #0284c7;"></span> Downstream State</div>
                <div><span class="legend-badge" style="background:#38bdf8;"></span> Reads</div>
                <div><span class="legend-badge" style="background:#f43f5e;"></span> Writes / Modifies</div>
            </div>
        </main>
    </div>

    <!-- Bottom Inspector Segment (Semantic UI Grid) -->
    <div class="app-inspector">
        <div class="inspector-col">
            <div class="inspector-title"><i class="info circle icon" style="color: #38bdf8;"></i> Target Variable Details</div>
            <div class="inspector-body" id="detailRootMeta">Select a variable from the sidebar to inspect complete data flow.</div>
        </div>
        <div class="inspector-col">
            <div class="inspector-title"><i class="eye icon" style="color: #38bdf8;"></i> Direct Function Readers</div>
            <div class="inspector-body" id="detailReaders">-</div>
        </div>
        <div class="inspector-col">
            <div class="inspector-title"><i class="pencil alternate icon" style="color: #f43f5e;"></i> Direct Function Writers / Modifiers</div>
            <div class="inspector-body" id="detailWriters">-</div>
        </div>
    </div>

    <script>
        const allGraphs = {all_graphs_json};
        const variablesSummary = {variables_summary_json};
        let currentRoot = "{initial_root}";
        let currentLayoutName = "dagre";
        let activeImpactFilter = "ALL";
        let cy = null;

        // Initialize Cytoscape Instance
        function initCytoscape() {{
            const container = document.getElementById("cy");
            const initialElements = allGraphs[currentRoot] || [];

            cy = cytoscape({{
                container: container,
                elements: initialElements,
                style: [
                    {{
                        selector: 'node',
                        style: {{
                            'label': 'data(label)',
                            'color': 'data(textColor)',
                            'font-family': 'monospace',
                            'font-size': '11px',
                            'font-weight': 'bold',
                            'text-valign': 'center',
                            'text-halign': 'center',
                            'background-color': 'data(bgColor)',
                            'border-color': 'data(borderColor)',
                            'border-width': 'data(borderWidth)',
                            'shape': 'data(shape)',
                            'width': 'label',
                            'height': '32px',
                            'padding': '12px',
                            'text-outline-color': 'data(bgColor)',
                            'text-outline-width': '1px',
                            'transition-property': 'background-color, border-color, width, height',
                            'transition-duration': '0.15s'
                        }}
                    }},
                    {{
                        selector: 'node:selected',
                        style: {{
                            'border-color': '#38bdf8',
                            'border-width': '4px',
                            'shadow-blur': 15,
                            'shadow-color': '#38bdf8',
                            'shadow-opacity': 0.8
                        }}
                    }},
                    {{
                        selector: 'edge',
                        style: {{
                            'width': 2,
                            'line-color': 'data(color)',
                            'target-arrow-color': 'data(color)',
                            'target-arrow-shape': 'triangle',
                            'curve-style': 'bezier',
                            'label': 'data(label)',
                            'font-family': 'monospace',
                            'font-size': '9px',
                            'color': '#94a3b8',
                            'text-background-color': '#0f172a',
                            'text-background-opacity': 0.85,
                            'text-background-padding': '2px',
                            'text-rotation': 'autorotate',
                            'line-style': 'data(lineStyle)'
                        }}
                    }},
                    {{
                        selector: 'edge:selected',
                        style: {{
                            'width': 4,
                            'line-color': '#38bdf8',
                            'target-arrow-color': '#38bdf8'
                        }}
                    }},
                    {{
                        selector: '.faded',
                        style: {{
                            'opacity': 0.15
                        }}
                    }},
                    {{
                        selector: '.highlighted',
                        style: {{
                            'opacity': 1.0,
                            'border-width': 4
                        }}
                    }}
                ],
                layout: getLayoutConfig('dagre'),
                wheelSensitivity: 0.25,
                minZoom: 0.2,
                maxZoom: 3.5
            }});

            // Event Listeners for Cytoscape
            cy.on('tap', 'node', function(evt) {{
                const node = evt.target;
                highlightNeighbors(node);
                showNodeInspector(node.data());
            }});

            cy.on('tap', function(evt) {{
                if (evt.target === cy) {{
                    cy.elements().removeClass('faded highlighted');
                    updateInspectorForRoot(currentRoot);
                }}
            }});
        }}

        function getLayoutConfig(name) {{
            if (name === 'dagre') {{
                return {{
                    name: 'dagre',
                    rankDir: 'TB',
                    nodeSep: 60,
                    rankSep: 80,
                    animate: true,
                    animationDuration: 300,
                    fit: true,
                    padding: 40
                }};
            }} else if (name === 'cola') {{
                return {{
                    name: 'cola',
                    animate: true,
                    maxSimulationTime: 1200,
                    fit: true,
                    padding: 40,
                    nodeSpacing: 45
                }};
            }} else if (name === 'breadthfirst') {{
                return {{
                    name: 'breadthfirst',
                    directed: true,
                    spacingFactor: 1.3,
                    animate: true,
                    fit: true,
                    padding: 40
                }};
            }} else if (name === 'concentric') {{
                return {{
                    name: 'concentric',
                    minNodeSpacing: 60,
                    animate: true,
                    fit: true,
                    padding: 40
                }};
            }}
            return {{ name: 'dagre', rankDir: 'TB' }};
        }}

        function applyLayout(name) {{
            currentLayoutName = name;
            document.querySelectorAll('.canvas-toolbar .ui.button').forEach(btn => btn.classList.remove('active'));
            const btnMap = {{
                'dagre': 'btnLayoutDagre',
                'cola': 'btnLayoutCola',
                'breadthfirst': 'btnLayoutBreadth',
                'concentric': 'btnLayoutConcentric'
            }};
            if (btnMap[name]) document.getElementById(btnMap[name]).classList.add('active');

            const layout = cy.layout(getLayoutConfig(name));
            layout.run();
        }}

        function synthesizeGraph(info) {{
            const elements = [];
            elements.push({{
                group: 'nodes',
                data: {{
                    id: info.name,
                    label: '⭐ ' + info.name,
                    name: info.name,
                    kind: 'variable',
                    node_type: 'variable',
                    is_root: true,
                    file_path: info.file_path,
                    line: info.line,
                    shape: 'round-rectangle',
                    bgColor: '#0284c7',
                    borderColor: '#38bdf8',
                    textColor: '#ffffff',
                    borderWidth: 3
                }}
            }});

            (info.readers || []).forEach((r, idx) => {{
                const rId = 'fn_' + r;
                elements.push({{
                    group: 'nodes',
                    data: {{
                        id: rId,
                        label: '⚙️ ' + r + '()',
                        name: r,
                        kind: 'function',
                        node_type: 'function',
                        is_root: false,
                        file_path: info.file_path,
                        line: info.line,
                        shape: 'round-rectangle',
                        bgColor: '#581c87',
                        borderColor: '#c084fc',
                        textColor: '#f3e8ff',
                        borderWidth: 2
                    }}
                }});
                elements.push({{
                    group: 'edges',
                    data: {{
                        id: 'e_r_' + idx,
                        source: info.name,
                        target: rId,
                        label: 'reads',
                        kind: 'READS',
                        color: '#38bdf8',
                        lineStyle: 'solid'
                    }}
                }});
            }});

            (info.writers || []).forEach((w, idx) => {{
                const wId = 'fn_' + w;
                elements.push({{
                    group: 'nodes',
                    data: {{
                        id: wId,
                        label: '⚙️ ' + w + '()',
                        name: w,
                        kind: 'function',
                        node_type: 'function',
                        is_root: false,
                        file_path: info.file_path,
                        line: info.line,
                        shape: 'round-rectangle',
                        bgColor: '#581c87',
                        borderColor: '#c084fc',
                        textColor: '#f3e8ff',
                        borderWidth: 2
                    }}
                }});
                elements.push({{
                    group: 'edges',
                    data: {{
                        id: 'e_w_' + idx,
                        source: wId,
                        target: info.name,
                        label: 'writes',
                        kind: 'WRITES',
                        color: '#f43f5e',
                        lineStyle: 'solid'
                    }}
                }});
            }});

            return elements;
        }}

        function selectVariable(varName) {{
            currentRoot = varName;
            renderVariableList();

            let elements = allGraphs[varName];
            if (!elements || elements.length === 0) {{
                const info = variablesSummary.find(v => v.name === varName);
                if (info) elements = synthesizeGraph(info);
            }}
            if (!elements) elements = [];

            cy.elements().remove();
            cy.add(elements);
            applyLayout(currentLayoutName);
            updateInspectorForRoot(varName);
        }}

        function highlightNeighbors(node) {{
            cy.elements().addClass('faded').removeClass('highlighted');
            node.removeClass('faded').addClass('highlighted');
            node.neighborhood().removeClass('faded').addClass('highlighted');
        }}

        function renderVariableList() {{
            const container = document.getElementById("varList");
            const query = document.getElementById("searchInput").value.toLowerCase();
            container.innerHTML = "";

            variablesSummary.forEach(v => {{
                if (activeImpactFilter !== "ALL" && v.impact_level !== activeImpactFilter) return;
                if (query && !v.name.toLowerCase().includes(query) && !v.file_path.toLowerCase().includes(query)) return;

                const card = document.createElement("div");
                card.className = `var-card ${{v.name === currentRoot ? 'active' : ''}}`;
                card.onclick = () => selectVariable(v.name);

                const fileName = v.file_path ? v.file_path.split("/").pop() + ":" + v.line : "global";
                
                let badgeClass = "grey";
                if (v.impact_level === "CRITICAL") badgeClass = "red";
                else if (v.impact_level === "HIGH") badgeClass = "orange";
                else if (v.impact_level === "MEDIUM") badgeClass = "teal";

                card.innerHTML = `
                    <div class="var-card-header">
                        <span class="var-name-text">🔷 ${{v.name}}</span>
                        <span class="ui mini ${{badgeClass}} label" style="padding: 3px 6px; font-size: 10px;">${{v.impact_level}}</span>
                    </div>
                    <div class="var-card-meta">
                        <span><i class="file code outline icon"></i> ${{fileName}}</span>
                        <span>Reach: <b>${{v.downstream_reach}}</b> | Depth: <b>${{v.max_depth}}</b></span>
                    </div>
                `;
                container.appendChild(card);
            }});
        }}

        function filterImpact(impact) {{
            activeImpactFilter = impact;
            document.querySelectorAll(".ui.pointing.menu a.item").forEach(tab => {{
                tab.classList.toggle("active", tab.innerText.toUpperCase() === impact);
            }});
            renderVariableList();
        }}

        function updateInspectorForRoot(varName) {{
            const info = variablesSummary.find(v => v.name === varName);
            if (!info) return;

            document.getElementById("detailRootMeta").innerHTML = `
                <div><b style="color: #38bdf8;">Variable:</b> <span class="code-tag">${{info.name}}</span></div>
                <div><b style="color: #94a3b8;">Location:</b> ${{info.file_path}}:${{info.line}}</div>
                <div><b style="color: #fbbf24;">Downstream Reach:</b> ${{info.downstream_reach}} elements | <b style="color: #c084fc;">Max Depth:</b> ${{info.max_depth}}</div>
            `;

            document.getElementById("detailReaders").innerHTML = info.readers && info.readers.length > 0 
                ? info.readers.map(r => `<span class="code-tag">⚙️ ${{r}}()</span>`).join(" ")
                : `<span style="color:#64748b;">No direct function readers.</span>`;

            document.getElementById("detailWriters").innerHTML = info.writers && info.writers.length > 0 
                ? info.writers.map(w => `<span class="code-tag" style="color:#f43f5e;">✏️ ${{w}}()</span>`).join(" ")
                : `<span style="color:#64748b;">No direct function writers.</span>`;
        }}

        function showNodeInspector(data) {{
            document.getElementById("detailRootMeta").innerHTML = `
                <div><b style="color: #38bdf8;">Selected Node:</b> <span class="code-tag">${{data.name}}</span></div>
                <div><b style="color: #94a3b8;">Kind:</b> ${{data.kind}} | <b style="color: #c084fc;">Type:</b> ${{data.node_type}}</div>
                <div><b style="color: #fbbf24;">Location:</b> ${{data.file_path || 'unknown'}}:${{data.line || 1}}</div>
            `;
        }}

        function exportPNG() {{
            const pngData = cy.png({{ scale: 2, full: true, bg: '#060911' }});
            const link = document.createElement('a');
            link.download = `dataflow_${{currentRoot}}.png`;
            link.href = pngData;
            link.click();
        }}

        function exportJSON() {{
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(cy.json(), null, 2));
            const downloadAnchor = document.createElement('a');
            downloadAnchor.setAttribute("href", dataStr);
            downloadAnchor.setAttribute("download", `dataflow_${{currentRoot}}.json`);
            document.body.appendChild(downloadAnchor);
            downloadAnchor.click();
            downloadAnchor.remove();
        }}

        // Initialization
        document.addEventListener("DOMContentLoaded", () => {{
            renderVariableList();
            initCytoscape();
            updateInspectorForRoot(currentRoot);

            document.getElementById("searchInput").addEventListener("input", renderVariableList);
        }});
    </script>
</body>
</html>
"""
