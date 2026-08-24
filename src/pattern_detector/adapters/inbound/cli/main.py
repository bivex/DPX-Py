"""Inbound Driving Adapter: CLI interface using Typer and Rich."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from pattern_detector.bootstrap.container import Container, create_container
from pattern_detector.domain.detection import DetectionReport
from pattern_detector.domain.insights import InsightSeverity, InsightsReport
from pattern_detector.domain.pattern import PATTERN_CATALOG
from pattern_detector.ports.inbound import ScanOptions

app = typer.Typer(
    name="pattern-detector",
    help="Hexagonal DDD Pattern Scanner & Detector for Python (Python 3.8-3.13+).",
    add_completion=False,
)
console = Console()


@app.command(name="scan")
def scan(
    path: Annotated[
        str,
        typer.Argument(
            help="File or directory path to scan for design patterns.",
        ),
    ] = ".",
    min_confidence: Annotated[
        float,
        typer.Option(
            "--min-confidence",
            "-c",
            help="Minimum confidence threshold (0.0 - 1.0).",
        ),
    ] = 0.0,
    pattern: Annotated[
        list[str] | None,
        typer.Option(
            "--pattern",
            "-p",
            help="Specific pattern types to look for (can be specified multiple times).",
        ),
    ] = None,
    json_output: Annotated[
        str | None,
        typer.Option(
            "--json",
            "-j",
            help="Export results to a JSON file destination.",
        ),
    ] = None,
    html_output: Annotated[
        str | None,
        typer.Option(
            "--html",
            "-H",
            help="Export results to an interactive HTML report dashboard.",
        ),
    ] = None,
    markdown_output: Annotated[
        str | None,
        typer.Option(
            "--markdown",
            "-m",
            help="Export results to a Markdown report file.",
        ),
    ] = None,
    sarif_output: Annotated[
        str | None,
        typer.Option(
            "--sarif",
            "-S",
            help="Export results to OASIS SARIF v2.1.0 JSON format for GitHub Code Scanning / CI-CD.",
        ),
    ] = None,
    insights: Annotated[
        bool,
        typer.Option(
            "--insights",
            "-I",
            help="Analyze pattern-dataflow interactions and generate actionable coder hints & code suggestions.",
        ),
    ] = False,
    llm: Annotated[
        bool,
        typer.Option(
            "--llm",
            "-L",
            help="Output token-efficient structured XML/Markdown context optimized for LLMs and AI coding agents.",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose output.",
        ),
    ] = False,
) -> None:
    """Scan a Python source code file or directory for software design patterns."""
    target_path = str(Path(path).resolve())

    container = create_container()
    scanner = container.get_scanner()

    options = ScanOptions(
        min_confidence=min_confidence,
        enabled_patterns=pattern or [],
        output_json_path=json_output,
        output_html_path=html_output,
        output_markdown_path=markdown_output,
        output_sarif_path=sarif_output,
        verbose=verbose,
    )

    if llm:
        report = scanner.scan_path(target_path, options=options)
        insights_report = container.scanning_service.generate_insights(target_path, report=report) if insights else None
        print(container.llm_formatter.format_scan_report(report, insights_report=insights_report))
        return

    with console.status(f"[cyan]Scanning [bold]{path}[/bold] using ANTLR parser & Domain Rules...[/cyan]"):
        report = scanner.scan_path(target_path, options=options)

    # Render formatted report to terminal
    container.report_formatter.render_to_console(report, console, verbose=verbose)  # type: ignore[attr-defined]

    if insights:
        _render_insights_to_console(container, target_path, report)

    if json_output:
        console.print(f"[bold green]✔[/bold green] Full JSON detection report exported to: [underline]{json_output}[/underline]")
    if html_output:
        console.print(f"[bold green]✔[/bold green] Interactive HTML dashboard exported to: [underline]{html_output}[/underline]")
    if markdown_output:
        console.print(f"[bold green]✔[/bold green] Markdown report exported to: [underline]{markdown_output}[/underline]")
    if sarif_output:
        console.print(f"[bold green]✔[/bold green] OASIS SARIF report exported to: [underline]{sarif_output}[/underline]")
    if json_output or html_output or markdown_output or sarif_output:
        console.print()


@app.command(name="rules")
def list_rules() -> None:
    """Display catalog of all registered pattern detection rules and heuristics."""
    table = Table(title="📐 Registered Design Pattern Rules & Heuristics", border_style="bright_blue", show_header=True)
    table.add_column("Pattern Type", style="bold cyan")
    table.add_column("Category", style="yellow")
    table.add_column("Intent & Detection Strategy", style="white")
    table.add_column("Tags", style="dim")

    for p_type, p_def in PATTERN_CATALOG.items():
        tags_str = ", ".join(p_def.tags)
        desc = f"[bold]{p_def.name}[/bold]\n{p_def.description}\n[dim]Intent: {p_def.intent}[/dim]"
        table.add_row(p_type.value, p_def.category.value.upper(), desc, tags_str)

    console.print(table)


@app.command(name="dataflow")
def dataflow(
    target: Annotated[
        str | None,
        typer.Argument(
            help="Target variable, field, or object. If omitted or '--all', analyzes ALL variables in file/project.",
        ),
    ] = None,
    path: Annotated[
        str,
        typer.Option(
            "--path",
            "-p",
            help="File or directory path containing Python source code.",
        ),
    ] = ".",
    all_vars: Annotated[
        bool,
        typer.Option(
            "--all",
            "-a",
            help="Analyze and summarize data flow for ALL variables in the file/project.",
        ),
    ] = False,
    file_filter: Annotated[
        str | None,
        typer.Option(
            "--file",
            "-f",
            help="Filter analysis to variables inside a specific source file.",
        ),
    ] = None,
    direction: Annotated[
        str,
        typer.Option(
            "--direction",
            "-d",
            help="Direction of data flow: 'out' (forward) or 'in' (backward).",
        ),
    ] = "out",
    variant: Annotated[
        str,
        typer.Option(
            "--variant",
            "-v",
            help="Visualization variant: 'simplified', 'cluster', 'relationship'.",
        ),
    ] = "simplified",
    to_entity: Annotated[
        str | None,
        typer.Option(
            "--to",
            help="Second entity to trace paths between (for relationship variant).",
        ),
    ] = None,
    mermaid: Annotated[
        bool,
        typer.Option(
            "--mermaid",
            "-m",
            help="Output Mermaid.js graph code.",
        ),
    ] = False,
    llm: Annotated[
        bool,
        typer.Option(
            "--llm",
            "-L",
            help="Output token-efficient structured XML/text context for LLMs and AI agents.",
        ),
    ] = False,
    html_output: Annotated[
        str | None,
        typer.Option(
            "--html",
            "-H",
            help="Export interactive HTML report using Vis.js visualizer.",
        ),
    ] = None,
    json_output: Annotated[
        str | None,
        typer.Option(
            "--json",
            "-j",
            help="Export graph or summary report data to a JSON file.",
        ),
    ] = None,
    max_depth: Annotated[
        int,
        typer.Option(
            "--max-depth",
            help="Maximum propagation traversal depth.",
        ),
    ] = 15,
) -> None:
    """Trace forward (Data Flow Out) or backward (Data Flow In) propagation graph for one or ALL variables."""
    # If target is actually an existing directory or file path, treat it as the analysis path
    if target and (os.path.isdir(target) or os.path.isfile(target)):
        target_path = str(Path(target).resolve())
        target = None
    else:
        target_path = str(Path(path).resolve())

    container = create_container()

    # If no target specified or --all requested: Analyze ALL variables
    if target is None or all_vars:
        summary_report = container.scanning_service.analyze_all_data_flows(
            target_path=target_path,
            direction=direction,
            file_filter=file_filter,
            max_depth=max_depth,
        )

        if llm:
            print(container.llm_formatter.format_data_flow_summary(summary_report))
            return

        console.print(summary_report.to_rich_table())

        if html_output:
            html_content = container.data_flow_html_formatter.format_summary_report(summary_report)
            Path(html_output).parent.mkdir(parents=True, exist_ok=True)
            with open(html_output, "w", encoding="utf-8") as f:
                f.write(html_content)
            console.print(f"\n[bold green]✔[/bold green] Interactive HTML report exported to: [underline]{html_output}[/underline]")

        if json_output:
            import json

            Path(json_output).parent.mkdir(parents=True, exist_ok=True)
            with open(json_output, "w", encoding="utf-8") as f:
                json.dump(summary_report.to_json(), f, indent=2)
            console.print(f"\n[bold green]✔[/bold green] Data flow summary JSON exported to: [underline]{json_output}[/underline]")
        return

    # Single variable flow analysis
    graph = container.scanning_service.analyze_data_flow(
        target_path=target_path,
        target_entity=target,
        direction=direction,
        variant=variant,
        to_entity=to_entity,
        max_depth=max_depth,
    )

    if llm:
        print(container.llm_formatter.format_data_flow_graph(graph))
        return

    if mermaid:
        console.print(f"[bold green]Mermaid Diagram for Data Flow ({graph.direction.value}):[/bold green]\n")
        console.print(f"```mermaid\n{graph.to_mermaid()}\n```")
    else:
        title = f"Data Flow {graph.direction.value}: '{target}'"
        if to_entity:
            title += f" ➔ '{to_entity}'"
        console.print(Panel(graph.to_rich_tree(), title=f"📊 [bold cyan]{title}[/bold cyan]", border_style="bright_blue"))

    if html_output:
        html_content = container.data_flow_html_formatter.format_single_graph(graph)
        Path(html_output).parent.mkdir(parents=True, exist_ok=True)
        with open(html_output, "w", encoding="utf-8") as f:
            f.write(html_content)
        console.print(f"\n[bold green]✔[/bold green] Interactive HTML report exported to: [underline]{html_output}[/underline]")

    if json_output:
        import json

        Path(json_output).parent.mkdir(parents=True, exist_ok=True)
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(graph.to_json(), f, indent=2)
        console.print(f"\n[bold green]✔[/bold green] Data flow graph JSON exported to: [underline]{json_output}[/underline]")


def _render_insights_to_console(
    container: Container,
    target_path: str,
    report: DetectionReport | None = None,
) -> None:
    """Render structured semantic insights and actionable coder suggestions to the console."""
    with console.status("[cyan]Analyzing Pattern-Dataflow interactions and synthesizing coder insights...[/cyan]"):
        insights_report: InsightsReport = container.scanning_service.generate_insights(
            target_path=target_path,
            report=report,
        )

    if not insights_report.insights:
        console.print("[dim]No actionable data-flow or architectural risks detected for current patterns.[/dim]")
        return

    console.print()
    console.print(
        f"💡 [bold white on blue] ARCHITECTURAL & DATA FLOW CODER INSIGHTS [/bold white on blue] "
        f"[bold cyan]{insights_report.total_insights}[/bold cyan] Recommendations "
        f"([red]{insights_report.critical_count} Critical[/red], "
        f"[yellow]{insights_report.warning_count} Warnings[/yellow], "
        f"[green]{insights_report.suggestion_count} Suggestions[/green])\n"
    )

    for i, ins in enumerate(insights_report.insights, start=1):
        sev_color = {
            InsightSeverity.CRITICAL: "red",
            InsightSeverity.WARNING: "yellow",
            InsightSeverity.SUGGESTION: "green",
            InsightSeverity.INFO: "blue",
        }.get(ins.severity, "white")

        sev_badge = f"[bold {sev_color}][{ins.severity.value}][/bold {sev_color}]"
        loc_str = f" [dim]({ins.location.file_path}:{ins.location.line})[/dim]" if ins.location and ins.location.file_path else ""

        body_lines: list[str] = [
            f"[bold]Target Pattern:[/bold] [magenta]{ins.target_pattern.value.upper()}[/magenta] on [cyan]{ins.target_name}[/cyan]{loc_str}",
            f"[bold]Data Entity / State:[/bold] [yellow]{ins.data_entity}[/yellow]",
            f"[bold]Analysis:[/bold] {ins.description}",
            "",
            f"👉 [bold green]Actionable Suggestion:[/bold green] {ins.suggestion}",
        ]

        if ins.affected_components:
            body_lines.append(f"[bold]Propagates to:[/bold] [dim]{', '.join(ins.affected_components)}[/dim]")

        content = "\n".join(body_lines)
        if ins.code_snippet:
            syntax_block = Syntax(ins.code_snippet, "python", theme="monokai", line_numbers=False)
            panel_content = Panel(
                f"{content}\n",
                title=f"#{i} {sev_badge} [bold white]{ins.title}[/bold white]",
                border_style=sev_color,
                subtitle="[dim]Python Recommended Implementation[/dim]",
            )
            console.print(panel_content)
            console.print(Panel(syntax_block, border_style="dim", title="[dim]Suggested Python Code[/dim]"))
        else:
            console.print(
                Panel(
                    content,
                    title=f"#{i} {sev_badge} [bold white]{ins.title}[/bold white]",
                    border_style=sev_color,
                )
            )


@app.command(name="insights")
def insights_cmd(
    path: Annotated[
        str,
        typer.Argument(
            help="File or directory path to analyze for pattern-dataflow insights.",
        ),
    ] = ".",
    llm: Annotated[
        bool,
        typer.Option(
            "--llm",
            "-L",
            help="Output token-efficient structured XML/Markdown context for LLMs.",
        ),
    ] = False,
) -> None:
    """Analyze the fusion of Design Patterns and Data Flow to deliver actionable developer hints."""
    target_path = str(Path(path).resolve())
    container = create_container()

    if llm:
        scanner = container.get_scanner()
        report = scanner.scan_path(target_path)
        insights_rep = container.scanning_service.generate_insights(target_path, report=report)
        print(container.llm_formatter.format_scan_report(report, insights_report=insights_rep))
        return

    _render_insights_to_console(container, target_path)


@app.command(name="info")
def info() -> None:
    """Display architecture info and supported grammar configurations."""
    info_text = (
        "[bold magenta]Pattern Scanner & Detector for Python (Hexagonal DDD Architecture)[/bold magenta]\n\n"
        "• [bold cyan]Core Domain:[/bold cyan] Agnostic CodeModel, Evidence & Confidence Score Engine, Specification Rules\n"
        "• [bold cyan]Inbound Ports:[/bold cyan] ScannerPort, DetectorPort, DataFlowPort\n"
        "• [bold cyan]Outbound Ports:[/bold cyan] ParserPort, SourceProviderPort, ResultRepositoryPort, ReportFormatterPort\n"
        "• [bold cyan]Active AST Adapter:[/bold cyan] Native Python AST Parser (Standard Library ast)\n"
        "• [bold cyan]Supported Extensions:[/bold cyan] .py, .pyi\n"
        "• [bold cyan]Features:[/bold cyan] 23/23 GoF Patterns, SOLID Principles, Data Flow Out / In Analysis, Coder Insights\n"
    )
    console.print(Panel(info_text, title="ℹ System Info", border_style="cyan"))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
