"""Inbound ports defining how driving adapters (CLI, API) interact with the application."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.data_flow import DataFlowGraph, DataFlowSummaryReport
from pattern_detector.domain.detection import Detection, DetectionReport


@dataclass
class ScanOptions:
    """Configuration options for a scanning session."""

    min_confidence: float = 0.0
    enabled_patterns: list[str] = field(default_factory=list)
    file_extensions: list[str] = field(default_factory=lambda: [".py", ".pyi"])
    output_json_path: str | None = None
    output_html_path: str | None = None
    output_markdown_path: str | None = None
    output_sarif_path: str | None = None
    exclude_dirs: list[str] = field(default_factory=list)
    verbose: bool = False



@dataclass
class DataFlowOptions:
    """Configuration options for data flow tracing."""

    direction: str = "OUT"
    variant: str = "simplified"
    to_entity: str | None = None
    max_depth: int = 15
    file_extensions: list[str] = field(default_factory=lambda: [".py", ".pyi"])


class ScannerPort(Protocol):
    """Inbound port for scanning a target path or repository."""

    def scan_path(self, target_path: str, options: ScanOptions | None = None) -> DetectionReport:
        """Scan a path (directory or single file) and return detection report."""
        ...


class DetectorPort(Protocol):
    """Inbound port for detecting patterns directly in an in-memory CodeModel."""

    def detect(self, model: CodeModel) -> list[Detection]:
        """Detect patterns in CodeModel."""
        ...


class DataFlowPort(Protocol):
    """Inbound port for tracing forward/backward Data Flow graphs."""

    def analyze_data_flow(
        self,
        target_path: str,
        target_entity: str,
        options: DataFlowOptions | None = None,
        **kwargs: Any,
    ) -> DataFlowGraph:
        """Trace data flow graph for target entity."""
        ...

    def analyze_all_data_flows(
        self,
        target_path: str,
        direction: str = "OUT",
        file_filter: str | None = None,
        max_depth: int = 15,
        file_extensions: list[str] | None = None,
    ) -> DataFlowSummaryReport:
        """Analyze data flow for all variables across a file or codebase."""
        ...
