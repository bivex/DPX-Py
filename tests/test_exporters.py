"""Tests for HTML and Markdown Report Formatters and Repositories."""

import tempfile
from pathlib import Path

from pattern_detector.adapters.outbound.persistence.file_result_repositories import (
    HtmlResultRepository,
    MarkdownResultRepository,
)
from pattern_detector.adapters.outbound.persistence.html_report_formatter import HtmlReportFormatter
from pattern_detector.adapters.outbound.persistence.markdown_report_formatter import MarkdownReportFormatter
from pattern_detector.bootstrap.container import create_container
from pattern_detector.domain.detection import Detection, DetectionReport
from pattern_detector.domain.value_objects import (
    Confidence,
    Evidence,
    PatternCategory,
    PatternType,
    SourceLocation,
)
from pattern_detector.ports.inbound import ScanOptions


def _create_sample_report() -> DetectionReport:
    loc = SourceLocation(file_path="src/app/Core.hpp", line=15, column=1)
    ev = Evidence(
        description="Watched atom with add-watch callback", weight=0.6, rule_code="WATCHED_STATE", location=loc
    )
    det = Detection(
        pattern_type=PatternType.OBSERVER,
        pattern_category=PatternCategory.BEHAVIORAL,
        target_name="system-state",
        target_kind="state_atom",
        confidence=Confidence.from_evidences([ev]),
        primary_location=loc,
        evidences=[ev],
    )
    return DetectionReport(
        project_path="src/app",
        scanned_files_count=1,
        detections=[det],
        elapsed_seconds=0.012,
    )


def test_html_report_formatter() -> None:
    formatter = HtmlReportFormatter()
    report = _create_sample_report()
    rendered = formatter.format(report)

    assert "<!DOCTYPE html>" in rendered
    assert "Pattern Scanner Report" in rendered
    assert "OBSERVER" in rendered
    assert "system-state" in rendered
    assert "WATCHED_STATE" in rendered


def test_markdown_report_formatter() -> None:
    formatter = MarkdownReportFormatter()
    report = _create_sample_report()
    rendered = formatter.format(report)

    assert "# 🔍 Software Design Pattern Detection Report" in rendered
    assert "OBSERVER" in rendered
    assert "system-state" in rendered
    assert "Evidence Trail" in rendered


def test_html_and_markdown_repositories_persistence() -> None:
    report = _create_sample_report()
    with tempfile.TemporaryDirectory() as tmpdir:
        html_file = str(Path(tmpdir) / "report.html")
        md_file = str(Path(tmpdir) / "report.md")

        HtmlResultRepository().save(report, html_file)
        MarkdownResultRepository().save(report, md_file)

        assert Path(html_file).exists()
        assert Path(md_file).exists()

        assert "<html" in Path(html_file).read_text(encoding="utf-8")
        assert "# 🔍" in Path(md_file).read_text(encoding="utf-8")


def test_cli_html_and_markdown_export() -> None:
    container = create_container()
    scanner = container.get_scanner()

    examples_dir = str(Path(__file__).parent.parent / "examples" / "python_samples")

    with tempfile.TemporaryDirectory() as tmpdir:
        html_out = str(Path(tmpdir) / "dashboard.html")
        md_out = str(Path(tmpdir) / "summary.md")

        opts = ScanOptions(
            output_html_path=html_out,
            output_markdown_path=md_out,
        )
        report = scanner.scan_path(examples_dir, options=opts)
        assert report.total_detections_count > 0

        assert Path(html_out).exists()
        assert Path(md_out).exists()


def test_llm_report_formatter() -> None:
    from typer.testing import CliRunner

    from pattern_detector.adapters.inbound.cli.main import app
    from pattern_detector.adapters.outbound.persistence.llm_report_formatter import LlmReportFormatter

    formatter = LlmReportFormatter()
    report = _create_sample_report()
    rendered = formatter.format_scan_report(report)

    assert "<codebase_architecture_analysis>" in rendered
    assert "<design_patterns>" in rendered
    assert 'type="observer"' in rendered
    assert 'target="system-state"' in rendered

    # Test CLI --llm flag
    runner = CliRunner()
    examples_dir = str(Path(__file__).parent.parent / "examples" / "python_samples")
    result = runner.invoke(app, ["scan", examples_dir, "--llm"])
    assert result.exit_code == 0
    assert "<codebase_architecture_analysis>" in result.stdout


def test_sarif_report_formatter() -> None:
    import json

    from pattern_detector.adapters.outbound.persistence.file_result_repositories import SarifResultRepository
    from pattern_detector.adapters.outbound.persistence.sarif_report_formatter import SarifReportFormatter

    formatter = SarifReportFormatter()
    report = _create_sample_report()
    rendered = formatter.format(report)

    sarif_data = json.loads(rendered)
    assert sarif_data["version"] == "2.1.0"
    assert len(sarif_data["runs"]) == 1
    assert sarif_data["runs"][0]["tool"]["driver"]["name"] == "DPX-Py"
    assert len(sarif_data["runs"][0]["results"]) == 1
    assert sarif_data["runs"][0]["results"][0]["ruleId"] == "DPX-OBSERVER"

    with tempfile.TemporaryDirectory() as tmpdir:
        sarif_file = str(Path(tmpdir) / "report.sarif")
        SarifResultRepository().save(report, sarif_file)
        assert Path(sarif_file).exists()
        loaded = json.loads(Path(sarif_file).read_text(encoding="utf-8"))
        assert loaded["version"] == "2.1.0"
