"""Application service coordinating the scanning pipeline."""

from __future__ import annotations

import time

from pattern_detector.domain.code_model import CodeModel
from pattern_detector.domain.data_flow import (
    DataFlowGraph,
    DataFlowSummaryReport,
    DataFlowVariant,
)
from pattern_detector.domain.detection import Detection, DetectionReport
from pattern_detector.domain.insights import InsightsReport
from pattern_detector.domain.services.data_flow import DataFlowService
from pattern_detector.domain.services.pattern_detector import PatternDetectorService
from pattern_detector.domain.services.pattern_insights import PatternInsightsService
from pattern_detector.ports.inbound import DataFlowPort, DetectorPort, ScannerPort, ScanOptions
from pattern_detector.ports.outbound import (
    ParserPort,
    ResultRepositoryPort,
    SourceProviderPort,
)


class ScanningService(ScannerPort, DetectorPort, DataFlowPort):
    """Application Service implementing ScannerPort, DetectorPort, and DataFlowPort.

    Coordinates source fetching, AST/C++ parsing into CodeModel,
    pattern rule execution, data flow analysis, and persisting results.
    """

    def __init__(
        self,
        source_provider: SourceProviderPort,
        parser: ParserPort,
        detector_service: PatternDetectorService,
        data_flow_service: DataFlowService | None = None,
        insights_service: PatternInsightsService | None = None,
        json_repository: ResultRepositoryPort | None = None,
        html_repository: ResultRepositoryPort | None = None,
        markdown_repository: ResultRepositoryPort | None = None,
        sarif_repository: ResultRepositoryPort | None = None,
    ) -> None:
        self._source_provider = source_provider
        self._parser = parser
        self._detector_service = detector_service
        self._data_flow_service = data_flow_service or DataFlowService()
        self._insights_service = insights_service or PatternInsightsService()
        self._json_repository = json_repository
        self._html_repository = html_repository
        self._markdown_repository = markdown_repository
        self._sarif_repository = sarif_repository

    def analyze_data_flow(
        self,
        target_path: str,
        target_entity: str,
        direction: str = "OUT",
        variant: str = "simplified",
        to_entity: str | None = None,
        max_depth: int = 15,
        file_extensions: list[str] | None = None,
    ) -> DataFlowGraph:
        """Trace data flow graph for target entity."""
        exts = file_extensions or [".py", ".pyi"]
        sources = self._source_provider.get_sources(target_path, extensions=exts)
        code_model = self._parser.parse_sources(sources)

        df_variant = (
            DataFlowVariant(variant.lower())
            if variant.lower() in [v.value for v in DataFlowVariant]
            else DataFlowVariant.SIMPLIFIED
        )

        if to_entity:
            return self._data_flow_service.trace_relationship(
                code_model, target_entity, to_entity, max_depth=max_depth
            )
        elif direction.upper() == "IN":
            return self._data_flow_service.trace_data_flow_in(
                code_model, target_entity, variant=df_variant, max_depth=max_depth
            )
        else:
            return self._data_flow_service.trace_data_flow_out(
                code_model, target_entity, variant=df_variant, max_depth=max_depth
            )

    def analyze_all_data_flows(
        self,
        target_path: str,
        direction: str = "OUT",
        file_filter: str | None = None,
        max_depth: int = 15,
        file_extensions: list[str] | None = None,
    ) -> DataFlowSummaryReport:
        """Analyze data flow for all variables across a file or codebase."""
        from pattern_detector.domain.data_flow import DataFlowDirection

        exts = file_extensions or [".py", ".pyi"]
        sources = self._source_provider.get_sources(target_path, extensions=exts)
        code_model = self._parser.parse_sources(sources)

        df_direction = DataFlowDirection.IN if direction.upper() == "IN" else DataFlowDirection.OUT
        return self._data_flow_service.analyze_all_variables(
            model=code_model,
            target_path=target_path,
            direction=df_direction,
            file_filter=file_filter,
            max_depth=max_depth,
        )

    def detect(self, model: CodeModel) -> list[Detection]:
        """Directly detect patterns in an already constructed CodeModel."""
        report = self._detector_service.detect_all(model)
        return report.detections

    def scan_path(self, target_path: str, options: ScanOptions | None = None) -> DetectionReport:
        """Execute full scan pipeline on given path."""
        start_time = time.perf_counter()
        opts = options or ScanOptions()

        # 1. Fetch sources via Outbound Port
        sources = self._source_provider.get_sources(target_path, extensions=opts.file_extensions)
        if not sources:
            return DetectionReport(
                project_path=target_path,
                scanned_files_count=0,
                detections=[],
                elapsed_seconds=round(time.perf_counter() - start_time, 4),
            )

        # 2. Parse sources into agnostic domain CodeModel via Outbound Port
        code_model = self._parser.parse_sources(sources)

        # 3. Execute domain detection rules
        report = self._detector_service.detect_all(code_model, project_path=target_path)
        total_elapsed = time.perf_counter() - start_time
        report.elapsed_seconds = total_elapsed

        # 4. Filter by confidence or pattern type if requested
        if opts.min_confidence > 0.0 or opts.enabled_patterns:
            filtered: list[Detection] = []
            for d in report.detections:
                if d.confidence.score < opts.min_confidence:
                    continue
                if opts.enabled_patterns and d.pattern_type.value not in opts.enabled_patterns:
                    continue
                filtered.append(d)
            report.detections = filtered

        # 5. Persist to outputs if requested
        if opts.output_json_path and self._json_repository:
            self._json_repository.save(report, opts.output_json_path)

        if opts.output_html_path and self._html_repository:
            self._html_repository.save(report, opts.output_html_path)

        if opts.output_markdown_path and self._markdown_repository:
            self._markdown_repository.save(report, opts.output_markdown_path)

        if opts.output_sarif_path and self._sarif_repository:
            self._sarif_repository.save(report, opts.output_sarif_path)

        return report

    def generate_insights(
        self,
        target_path: str,
        report: DetectionReport | None = None,
        include_data_flow: bool = True,
        file_extensions: list[str] | None = None,
    ) -> InsightsReport:
        """Analyze pattern-data interactions and generate actionable coder insights."""
        exts = file_extensions or [".py", ".pyi"]
        sources = self._source_provider.get_sources(target_path, extensions=exts)
        code_model = self._parser.parse_sources(sources)

        det_report = report or self._detector_service.detect_all(code_model, project_path=target_path)
        df_summary = (
            self._data_flow_service.analyze_all_variables(code_model, target_path=target_path)
            if include_data_flow
            else None
        )

        return self._insights_service.generate_insights(
            model=code_model,
            pattern_report=det_report,
            data_flow_summary=df_summary,
        )
