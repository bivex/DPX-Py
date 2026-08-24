"""Tests for Data Flow Analysis in Python."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from pattern_detector.adapters.inbound.cli.main import app
from pattern_detector.adapters.outbound.python_ast.py_parser_adapter import PyParserAdapter
from pattern_detector.domain.data_flow import (
    DataFlowDirection,
    DataFlowVariant,
)
from pattern_detector.domain.services.data_flow import DataFlowService

SAMPLE_PY = """
aux_data = 0
transformed_data = 0
output_result = 0
log_buffer = 0
running_total = 0
report_value = 0

def normalize() -> None:
    global transformed_data
    if transformed_data > 100:
        transformed_data = 100
    else:
        transformed_data = transformed_data + aux_data

def output() -> None:
    global output_result
    output_result = transformed_data

def log_data() -> None:
    global log_buffer
    log_buffer += transformed_data

def accumulate() -> None:
    global running_total
    running_total += output_result

def report() -> None:
    global report_value
    report_value = running_total
"""


def test_data_flow_out_extraction_and_graph() -> None:
    adapter = PyParserAdapter()
    model = adapter.parse_sources({"sample.py": SAMPLE_PY})

    # Verify states and functions
    states = [s.name for s in model.all_states()]
    assert "transformed_data" in states
    assert "output_result" in states
    assert "running_total" in states
    assert "report_value" in states

    service = DataFlowService()
    graph = service.trace_data_flow_out(model, "transformed_data")

    assert graph.direction == DataFlowDirection.OUT
    assert graph.root_id == "transformed_data"
    assert "transformed_data" in graph.nodes
    assert "fn_normalize" in graph.nodes
    assert "fn_output" in graph.nodes
    assert "output_result" in graph.nodes
    assert "fn_accumulate" in graph.nodes
    assert "running_total" in graph.nodes
    assert "fn_report" in graph.nodes
    assert "report_value" in graph.nodes

    # Check edges
    edge_pairs = [(e.from_id, e.to_id, e.kind) for e in graph.edges]
    assert ("transformed_data", "fn_normalize", "READS") in edge_pairs
    assert ("transformed_data", "fn_output", "READS") in edge_pairs
    assert ("fn_output", "output_result", "WRITES") in edge_pairs
    assert ("output_result", "fn_accumulate", "READS") in edge_pairs
    assert ("fn_accumulate", "running_total", "MODIFIES") in edge_pairs
    assert ("running_total", "fn_report", "READS") in edge_pairs
    assert ("fn_report", "report_value", "WRITES") in edge_pairs


def test_data_flow_in_backward_slice() -> None:
    adapter = PyParserAdapter()
    model = adapter.parse_sources({"sample.py": SAMPLE_PY})

    service = DataFlowService()
    graph = service.trace_data_flow_in(model, "report_value")

    assert graph.direction == DataFlowDirection.IN
    assert graph.root_id == "report_value"
    assert "report_value" in graph.nodes
    assert "fn_report" in graph.nodes
    assert "running_total" in graph.nodes
    assert "fn_accumulate" in graph.nodes
    assert "output_result" in graph.nodes
    assert "fn_output" in graph.nodes
    assert "transformed_data" in graph.nodes


def test_data_flow_relationship_path() -> None:
    adapter = PyParserAdapter()
    model = adapter.parse_sources({"sample.py": SAMPLE_PY})

    service = DataFlowService()
    graph = service.trace_relationship(model, source="transformed_data", target="report_value")

    assert graph.variant == DataFlowVariant.RELATIONSHIP
    assert "transformed_data" in graph.nodes
    assert "report_value" in graph.nodes
    # Should contain intermediate chain nodes
    assert "output_result" in graph.nodes
    assert "running_total" in graph.nodes
    # But log_buffer should NOT be in the path to report_value
    assert "log_buffer" not in graph.nodes


def test_data_flow_mermaid_rendering() -> None:
    adapter = PyParserAdapter()
    model = adapter.parse_sources({"sample.py": SAMPLE_PY})

    service = DataFlowService()
    graph = service.trace_data_flow_out(model, "transformed_data")
    mermaid = graph.to_mermaid(direction_layout="LR")

    assert "graph LR" in mermaid
    assert "transformed_data" in mermaid
    assert "report_value" in mermaid
    assert "reads" in mermaid
    assert "writes" in mermaid


def test_data_flow_cli_command(tmp_path: Path) -> None:
    runner = CliRunner()
    sample_file = tmp_path / "data_flow_sample.py"
    sample_file.write_text(SAMPLE_PY)

    # Test CLI dataflow command
    result = runner.invoke(app, ["dataflow", "transformed_data", "--path", str(sample_file)])
    assert result.exit_code == 0
    assert "transformed_data" in result.stdout
    assert "output_result" in result.stdout

    # Test CLI mermaid output
    result_m = runner.invoke(app, ["dataflow", "transformed_data", "--path", str(sample_file), "--mermaid"])
    assert result_m.exit_code == 0
    assert "```mermaid" in result_m.stdout
    assert "graph LR" in result_m.stdout

    # Test CLI JSON output
    json_dest = tmp_path / "df.json"
    result_j = runner.invoke(
        app, ["dataflow", "transformed_data", "--path", str(sample_file), "--json", str(json_dest)]
    )
    assert result_j.exit_code == 0
    assert json_dest.exists()


def test_data_flow_all_variables_summary_matrix(tmp_path: Path) -> None:
    runner = CliRunner()
    sample_file = tmp_path / "data_flow_batch.py"
    sample_file.write_text(SAMPLE_PY)

    # Test CLI dataflow --all
    result_all = runner.invoke(app, ["dataflow", "--all", "--path", str(sample_file)])
    assert result_all.exit_code == 0
    assert "Data Flow Summary Matrix" in result_all.stdout
    assert "aux_data" in result_all.stdout
    assert "transformed_data" in result_all.stdout
    assert "output_result" in result_all.stdout
    assert "running_total" in result_all.stdout

    # Test summary JSON output
    json_dest = tmp_path / "summary.json"
    result_json = runner.invoke(app, ["dataflow", "--all", "--path", str(sample_file), "--json", str(json_dest)])
    assert result_json.exit_code == 0
    assert json_dest.exists()


def test_data_flow_html_report_export(tmp_path: Path) -> None:
    runner = CliRunner()
    sample_file = tmp_path / "data_flow_html_sample.py"
    sample_file.write_text(SAMPLE_PY)

    # 1. Test single-variable HTML export
    html_single = tmp_path / "single_flow.html"
    res_single = runner.invoke(
        app, ["dataflow", "transformed_data", "--path", str(sample_file), "--html", str(html_single)]
    )
    assert res_single.exit_code == 0
    assert html_single.exists()
    content_single = html_single.read_text(encoding="utf-8")
    assert "vis.Network" in content_single
    assert "transformed_data" in content_single

    # 2. Test batch summary HTML export
    html_all = tmp_path / "all_flows.html"
    res_all = runner.invoke(app, ["dataflow", "--all", "--path", str(sample_file), "--html", str(html_all)])
    assert res_all.exit_code == 0
    assert html_all.exists()
    content_all = html_all.read_text(encoding="utf-8")
    assert "vis.Network" in content_all
    assert "aux_data" in content_all
    assert "report_value" in content_all


def test_data_flow_llm_output(tmp_path: Path) -> None:
    runner = CliRunner()
    sample_file = tmp_path / "data_flow_llm_sample.py"
    sample_file.write_text(SAMPLE_PY)

    # 1. Single variable --llm
    res_single = runner.invoke(app, ["dataflow", "transformed_data", "--path", str(sample_file), "--llm"])
    assert res_single.exit_code == 0
    assert '<data_flow_analysis direction="OUT" root_variable="transformed_data">' in res_single.stdout
    assert "<direct_readers" in res_single.stdout
    assert "<propagation_paths>" in res_single.stdout

    # 2. All variables --llm
    res_all = runner.invoke(app, ["dataflow", "--all", "--path", str(sample_file), "--llm"])
    assert res_all.exit_code == 0
    assert "<data_flow_project_summary" in res_all.stdout
    assert 'name="transformed_data"' in res_all.stdout
    assert 'name="running_total"' in res_all.stdout
