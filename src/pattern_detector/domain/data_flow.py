"""Data Flow Domain Models and Graphs (SciTools Understand Data Flow Out / In Parity)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from rich.tree import Tree

from pattern_detector.domain.value_objects import SourceLocation


class DataFlowDirection(str, Enum):
    """Direction of the data flow analysis."""

    OUT = "OUT"  # Forward data flow: what reads and propagates this variable
    IN = "IN"    # Backward data flow: what sources / functions affect this variable


class DataFlowVariant(str, Enum):
    """Visualization and graph structuring variants."""

    SIMPLIFIED = "simplified"      # Simple tree / DAG without cluster boxes
    CLUSTER = "cluster"            # Group entities by file / class / namespace
    RELATIONSHIP = "relationship"  # Only paths connecting two specific entities


class NodeKind(str, Enum):
    """Kind of graph node."""

    VARIABLE = "variable"
    FUNCTION = "function"


@dataclass
class DataFlowNode:
    """Represents a node (variable or function) in the data flow graph."""

    id: str
    name: str
    kind: NodeKind
    cluster: str = "default"
    file_path: str = ""
    line: int = 1
    is_root: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DataFlowEdge:
    """Represents a directional flow between a variable and a function."""

    from_id: str
    to_id: str
    kind: str  # "READS", "WRITES", "MODIFIES"
    location: SourceLocation | None = None


@dataclass
class DataFlowGraph:
    """Complete Data Flow Out/In Graph representation."""

    root_id: str
    direction: DataFlowDirection = DataFlowDirection.OUT
    variant: DataFlowVariant = DataFlowVariant.SIMPLIFIED
    nodes: dict[str, DataFlowNode] = field(default_factory=dict)
    edges: list[DataFlowEdge] = field(default_factory=list)
    max_depth: int = 0
    _edge_set: set[tuple[str, str, str]] = field(default_factory=set, repr=False)

    def add_node(
        self,
        node_id: str,
        name: str,
        kind: NodeKind,
        cluster: str = "default",
        file_path: str = "",
        line: int = 1,
        is_root: bool = False,
    ) -> DataFlowNode:
        if node_id not in self.nodes:
            self.nodes[node_id] = DataFlowNode(
                id=node_id,
                name=name,
                kind=kind,
                cluster=cluster,
                file_path=file_path,
                line=line,
                is_root=is_root,
            )
        return self.nodes[node_id]

    def add_edge(self, from_id: str, to_id: str, kind: str, location: SourceLocation | None = None) -> None:
        key = (from_id, to_id, kind)
        if key not in self._edge_set:
            self._edge_set.add(key)
            self.edges.append(DataFlowEdge(from_id=from_id, to_id=to_id, kind=kind, location=location))

    def to_mermaid(self, direction_layout: str = "LR") -> str:
        """Render graph to clean Mermaid.js diagram."""
        lines = [f"graph {direction_layout}"]
        lines.append("    %% Styles")
        lines.append("    classDef rootNode fill:#0284c7,stroke:#38bdf8,stroke-width:3px,color:#ffffff,font-weight:bold;")
        lines.append("    classDef varNode fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;")
        lines.append("    classDef fnNode fill:#0f172a,stroke:#c084fc,stroke-width:2px,color:#f8fafc;")

        # Group by cluster if CLUSTER variant
        if self.variant == DataFlowVariant.CLUSTER:
            clusters: dict[str, list[DataFlowNode]] = {}
            for node in self.nodes.values():
                clusters.setdefault(node.cluster or "global", []).append(node)

            for c_name, c_nodes in clusters.items():
                sanitized_cname = "".join(c if c.isalnum() else "_" for c in c_name)
                lines.append(f"    subgraph cluster_{sanitized_cname} [\"{c_name}\"]")
                for node in c_nodes:
                    node_esc = node.name.replace('"', '\\"')
                    icon = "🔷" if node.kind == NodeKind.VARIABLE else "⚙️"
                    lines.append(f"        {node.id}[\"{icon} {node_esc}\"]")
                lines.append("    end")
        else:
            for node in self.nodes.values():
                node_esc = node.name.replace('"', '\\"')
                icon = "🔷" if node.kind == NodeKind.VARIABLE else "⚙️"
                lines.append(f"    {node.id}[\"{icon} {node_esc}\"]")

        # Edges
        for edge in self.edges:
            label = edge.kind.lower()
            if edge.kind == "MODIFIES":
                lines.append(f"    {edge.from_id} -.->|{label}| {edge.to_id}")
            else:
                lines.append(f"    {edge.from_id} -->|{label}| {edge.to_id}")

        # Apply classes
        for node in self.nodes.values():
            if node.is_root:
                lines.append(f"    class {node.id} rootNode;")
            elif node.kind == NodeKind.VARIABLE:
                lines.append(f"    class {node.id} varNode;")
            else:
                lines.append(f"    class {node.id} fnNode;")

        return "\n".join(lines)

    def to_rich_tree(self) -> Tree:
        """Render graph as an interactive Rich ASCII Tree for terminal output."""
        root_node = self.nodes.get(self.root_id)
        root_label = f"[bold cyan]🔷 {self.root_id}[/bold cyan] [dim]({self.direction.value})[/dim]" if root_node else f"[bold]{self.root_id}[/bold]"
        tree = Tree(root_label)

        # Adjacency map
        adj: dict[str, list[DataFlowEdge]] = {}
        for edge in self.edges:
            adj.setdefault(edge.from_id, []).append(edge)

        visited: set[str] = set()

        def build_branch(parent_id: str, branch: Tree, depth: int) -> None:
            if depth > 12:
                return
            for edge in adj.get(parent_id, []):
                child_id = edge.to_id
                child_node = self.nodes.get(child_id)
                kind_str = f"[dim]({edge.kind.lower()})[/dim]"
                if child_node and child_node.kind == NodeKind.FUNCTION:
                    label = f"⚙️ [bold magenta]{child_node.name}()[/bold magenta] {kind_str}"
                else:
                    label = f"🔷 [bold yellow]{child_id}[/bold yellow] {kind_str}"

                if child_id == parent_id or child_id in visited and depth > 2:
                    branch.add(f"{label} [dim red]↺ (cycle)[/dim red]")
                    continue

                visited.add(child_id)
                sub_branch = branch.add(label)
                build_branch(child_id, sub_branch, depth + 1)

        build_branch(self.root_id, tree, 1)
        return tree

    def to_json(self) -> dict[str, Any]:
        """Serialize data flow graph to JSON dict."""
        return {
            "root": self.root_id,
            "direction": self.direction.value,
            "variant": self.variant.value,
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "kind": n.kind.value,
                    "cluster": n.cluster,
                    "file_path": n.file_path,
                    "line": n.line,
                    "is_root": n.is_root,
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "from": e.from_id,
                    "to": e.to_id,
                    "kind": e.kind,
                    "location": f"{e.location.file_path}:{e.location.line}" if e.location else None,
                }
                for e in self.edges
            ],
        }


@dataclass
class VariableFlowSummary:
    """Summary of data flow characteristics for a single variable."""

    name: str
    file_path: str = ""
    line: int = 1
    readers: list[str] = field(default_factory=list)
    writers: list[str] = field(default_factory=list)
    downstream_reach: int = 0
    max_depth: int = 0
    impact_level: str = "LOW"  # CRITICAL, HIGH, MEDIUM, LOW
    graph: DataFlowGraph | None = None


@dataclass
class DataFlowSummaryReport:
    """Project or file-level data flow analysis summary across all variables."""

    target_path: str
    direction: DataFlowDirection = DataFlowDirection.OUT
    summaries: list[VariableFlowSummary] = field(default_factory=list)
    total_variables: int = 0
    total_edges: int = 0

    def to_rich_table(self) -> Any:
        """Render summary report as a Rich Table."""
        from rich.table import Table

        title = f"🌲 Data Flow Summary Matrix ({self.direction.value}): {self.total_variables} Variables Analyzed"
        table = Table(title=title, border_style="bright_blue", show_header=True, header_style="bold cyan")
        table.add_column("Variable / Field", style="bold yellow", no_wrap=True)
        table.add_column("Location", style="dim")
        table.add_column("Readers", justify="center")
        table.add_column("Writers", justify="center")
        table.add_column("Reach (Nodes)", justify="center", style="magenta")
        table.add_column("Max Depth", justify="center")
        table.add_column("Impact Level", justify="center")

        for s in sorted(self.summaries, key=lambda x: (x.downstream_reach, len(x.readers)), reverse=True):
            loc_str = f"{s.file_path.split('/')[-1]}:{s.line}" if s.file_path else "global"
            if s.impact_level == "CRITICAL":
                impact_styled = "[bold red]CRITICAL[/bold red]"
            elif s.impact_level == "HIGH":
                impact_styled = "[bold yellow]HIGH[/bold yellow]"
            elif s.impact_level == "MEDIUM":
                impact_styled = "[cyan]MEDIUM[/cyan]"
            else:
                impact_styled = "[dim]LOW[/dim]"

            readers_str = f"{len(s.readers)} fn" if s.readers else "[dim]0[/dim]"
            writers_str = f"{len(s.writers)} fn" if s.writers else "[dim]0[/dim]"

            table.add_row(
                s.name,
                loc_str,
                readers_str,
                writers_str,
                str(s.downstream_reach),
                str(s.max_depth),
                impact_styled,
            )

        return table

    def to_json(self) -> dict[str, Any]:
        """Serialize report to JSON."""
        return {
            "target_path": self.target_path,
            "direction": self.direction.value,
            "total_variables": self.total_variables,
            "total_edges": self.total_edges,
            "variables": [
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
                for s in self.summaries
            ],
        }

