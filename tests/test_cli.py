"""Tests for Typer CLI commands in Python Pattern Detector."""

from typer.testing import CliRunner

from pattern_detector.adapters.inbound.cli.main import app

runner = CliRunner()


def test_cli_rules_command() -> None:
    result = runner.invoke(app, ["rules"])
    assert result.exit_code == 0
    assert "Registered Design Pattern Rules" in result.stdout
    assert "observer" in result.stdout
    assert "strategy" in result.stdout


def test_cli_info_command() -> None:
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "Hexagonal DDD Architecture" in result.stdout
    assert "Python AST Parser" in result.stdout


def test_cli_scan_command() -> None:
    result = runner.invoke(app, ["scan", "examples/python_samples"])
    assert result.exit_code == 0
    assert "Detection Summary" in result.stdout
    assert "Identified Design Patterns" in result.stdout
