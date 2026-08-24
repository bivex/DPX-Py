"""Bootstrap DI Container / Composition Root."""

from __future__ import annotations

from typing import Any

from pattern_detector.adapters.outbound.filesystem import FileSourceProvider
from pattern_detector.adapters.outbound.persistence import (
    ConsoleReportFormatter,
    DataFlowHtmlFormatter,
    HtmlReportFormatter,
    HtmlResultRepository,
    JsonResultRepository,
    LlmReportFormatter,
    MarkdownReportFormatter,
    MarkdownResultRepository,
    SarifReportFormatter,
    SarifResultRepository,
)
from pattern_detector.adapters.outbound.python_ast import PyParserAdapter
from pattern_detector.application.services.scanning_service import ScanningService
from pattern_detector.domain.rules import get_default_rules
from pattern_detector.domain.services.data_flow import DataFlowService
from pattern_detector.domain.services.pattern_detector import PatternDetectorService
from pattern_detector.domain.services.pattern_insights import PatternInsightsService
from pattern_detector.ports.inbound import ScannerPort
from pattern_detector.ports.outbound import (
    ParserPort,
    ReportFormatterPort,
    ResultRepositoryPort,
    SourceProviderPort,
)


class Container:
    """Dependency Injection Container and Composition Root.

    Instantiates and wires domain services, driven outbound adapters,
    and application use cases adhering to Hexagonal Architecture.
    """

    def __init__(self, **components: Any) -> None:
        # Outbound Driven Adapters
        self.source_provider: SourceProviderPort = components.get("source_provider") or FileSourceProvider()
        self.parser: ParserPort = components.get("parser") or PyParserAdapter()

        self.html_formatter: ReportFormatterPort = components.get("html_formatter") or HtmlReportFormatter()
        self.data_flow_html_formatter: DataFlowHtmlFormatter = (
            components.get("data_flow_html_formatter") or DataFlowHtmlFormatter()
        )
        self.llm_formatter: LlmReportFormatter = components.get("llm_formatter") or LlmReportFormatter()
        self.markdown_formatter: ReportFormatterPort = components.get("markdown_formatter") or MarkdownReportFormatter()
        self.sarif_formatter: SarifReportFormatter = components.get("sarif_formatter") or SarifReportFormatter()
        self.report_formatter: ReportFormatterPort = components.get("report_formatter") or ConsoleReportFormatter()

        self.json_repository: ResultRepositoryPort = components.get("json_repository") or JsonResultRepository()
        self.html_repository: ResultRepositoryPort = components.get("html_repository") or HtmlResultRepository(
            formatter=self.html_formatter
        )  # type: ignore[arg-type]
        self.markdown_repository: ResultRepositoryPort = components.get(
            "markdown_repository"
        ) or MarkdownResultRepository(formatter=self.markdown_formatter)  # type: ignore[arg-type]
        self.sarif_repository: ResultRepositoryPort = components.get("sarif_repository") or SarifResultRepository(
            formatter=self.sarif_formatter
        )

        # Domain Service & Rules
        self.detector_service: PatternDetectorService = components.get("detector_service") or PatternDetectorService(
            rules=get_default_rules()
        )
        self.data_flow_service: DataFlowService = DataFlowService()
        self.insights_service: PatternInsightsService = PatternInsightsService()

        # Application Service (Inbound Port implementation)
        self.scanning_service: ScanningService = ScanningService(
            source_provider=self.source_provider,
            parser=self.parser,
            detector_service=self.detector_service,
            data_flow_service=self.data_flow_service,
            insights_service=self.insights_service,
            json_repository=self.json_repository,
            html_repository=self.html_repository,
            markdown_repository=self.markdown_repository,
            sarif_repository=self.sarif_repository,
        )

    def get_scanner(self) -> ScannerPort:
        return self.scanning_service

    def get_formatter(self) -> ReportFormatterPort:
        return self.report_formatter


def create_container() -> Container:
    """Create a default production container."""
    return Container()
