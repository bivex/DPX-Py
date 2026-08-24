"""Bootstrap DI Container / Composition Root."""

from __future__ import annotations

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

    def __init__(
        self,
        source_provider: SourceProviderPort | None = None,
        parser: ParserPort | None = None,
        json_repository: ResultRepositoryPort | None = None,
        html_repository: ResultRepositoryPort | None = None,
        markdown_repository: ResultRepositoryPort | None = None,
        sarif_repository: ResultRepositoryPort | None = None,
        report_formatter: ReportFormatterPort | None = None,
        html_formatter: ReportFormatterPort | None = None,
        markdown_formatter: ReportFormatterPort | None = None,
        sarif_formatter: SarifReportFormatter | None = None,
        data_flow_html_formatter: DataFlowHtmlFormatter | None = None,
        llm_formatter: LlmReportFormatter | None = None,
        detector_service: PatternDetectorService | None = None,
    ) -> None:
        # Outbound Driven Adapters
        self.source_provider: SourceProviderPort = source_provider or FileSourceProvider()
        self.parser: ParserPort = parser or PyParserAdapter()

        self.html_formatter: ReportFormatterPort = html_formatter or HtmlReportFormatter()
        self.data_flow_html_formatter: DataFlowHtmlFormatter = data_flow_html_formatter or DataFlowHtmlFormatter()
        self.llm_formatter: LlmReportFormatter = llm_formatter or LlmReportFormatter()
        self.markdown_formatter: ReportFormatterPort = markdown_formatter or MarkdownReportFormatter()
        self.sarif_formatter: SarifReportFormatter = sarif_formatter or SarifReportFormatter()
        self.report_formatter: ReportFormatterPort = report_formatter or ConsoleReportFormatter()

        self.json_repository: ResultRepositoryPort = json_repository or JsonResultRepository()
        self.html_repository: ResultRepositoryPort = html_repository or HtmlResultRepository(
            formatter=self.html_formatter
        )  # type: ignore[arg-type]
        self.markdown_repository: ResultRepositoryPort = markdown_repository or MarkdownResultRepository(
            formatter=self.markdown_formatter
        )  # type: ignore[arg-type]
        self.sarif_repository: ResultRepositoryPort = sarif_repository or SarifResultRepository(
            formatter=self.sarif_formatter
        )

        # Domain Service & Rules
        self.detector_service: PatternDetectorService = detector_service or PatternDetectorService(
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
