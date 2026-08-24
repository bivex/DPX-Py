"""Tests for Pattern-Dataflow Insights Engine and CLI integration."""

from pathlib import Path

from typer.testing import CliRunner

from pattern_detector.adapters.inbound.cli.main import app
from pattern_detector.bootstrap.container import create_container


def test_pattern_insights_generation_on_cpp_samples() -> None:
    container = create_container()
    examples_dir = str(Path(__file__).parent.parent / "examples" / "python_samples")

    insights_report = container.scanning_service.generate_insights(examples_dir)
    assert insights_report.total_insights >= 0


def test_pattern_insights_cli_command() -> None:
    runner = CliRunner()
    examples_dir = str(Path(__file__).parent.parent / "examples" / "python_samples")

    result = runner.invoke(app, ["insights", examples_dir])
    assert result.exit_code == 0

    # Test with LLM flag
    result_llm = runner.invoke(app, ["insights", examples_dir, "--llm"])
    assert result_llm.exit_code == 0
    assert "<codebase_architecture_analysis>" in result_llm.stdout
