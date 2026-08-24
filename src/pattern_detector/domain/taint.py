"""Taint Analysis Domain Models, Source/Sink Catalog, and Vulnerability Flow Definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from pattern_detector.domain.value_objects import SourceLocation


class TaintCategory(str, Enum):
    """Categories of security and architectural taint vulnerabilities."""

    SQL_INJECTION = "sql_injection"
    COMMAND_INJECTION = "command_injection"
    CODE_INJECTION = "code_injection"
    PATH_TRAVERSAL = "path_traversal"
    SSRF = "ssrf"
    SENSITIVE_DATA_LEAK = "sensitive_data_leak"
    UNVALIDATED_INPUT = "unvalidated_input"


@dataclass(frozen=True)
class TaintSourcePattern:
    """Pattern identifying an untrusted or sensitive data entrypoint."""

    pattern: str  # substring or regex matching variable, attribute, or call
    category: TaintCategory
    description: str
    is_sensitive: bool = False


@dataclass(frozen=True)
class TaintSinkPattern:
    """Pattern identifying a dangerous operation or sensitive sink."""

    pattern: str  # function or method name (e.g. 'cursor.execute', 'subprocess.run')
    category: TaintCategory
    severity: str  # 'CRITICAL', 'HIGH', 'MEDIUM'
    cwe_id: str  # e.g. 'CWE-89'
    description: str


# Standard Python Taint Sources Catalog
DEFAULT_TAINT_SOURCES: tuple[TaintSourcePattern, ...] = (
    # HTTP Inputs
    TaintSourcePattern("request.json", TaintCategory.UNVALIDATED_INPUT, "HTTP JSON payload body"),
    TaintSourcePattern("request.args", TaintCategory.UNVALIDATED_INPUT, "HTTP query parameters"),
    TaintSourcePattern("request.form", TaintCategory.UNVALIDATED_INPUT, "HTTP form data"),
    TaintSourcePattern("request.values", TaintCategory.UNVALIDATED_INPUT, "HTTP request values"),
    TaintSourcePattern("request.data", TaintCategory.UNVALIDATED_INPUT, "HTTP raw data payload"),
    TaintSourcePattern("request.query_params", TaintCategory.UNVALIDATED_INPUT, "FastAPI / Starlette query parameters"),
    TaintSourcePattern("request.headers", TaintCategory.UNVALIDATED_INPUT, "HTTP request headers"),
    # CLI & Environment
    TaintSourcePattern("sys.argv", TaintCategory.UNVALIDATED_INPUT, "Command-line arguments"),
    TaintSourcePattern("os.environ", TaintCategory.UNVALIDATED_INPUT, "Environment variable"),
    TaintSourcePattern("os.getenv", TaintCategory.UNVALIDATED_INPUT, "Environment variable lookup"),
    TaintSourcePattern("input(", TaintCategory.UNVALIDATED_INPUT, "Interactive standard input"),
    # Sensitive Data Sources
    TaintSourcePattern("password", TaintCategory.SENSITIVE_DATA_LEAK, "Sensitive password field", is_sensitive=True),
    TaintSourcePattern("token", TaintCategory.SENSITIVE_DATA_LEAK, "Sensitive authentication token", is_sensitive=True),
    TaintSourcePattern("api_key", TaintCategory.SENSITIVE_DATA_LEAK, "Sensitive API key secret", is_sensitive=True),
    TaintSourcePattern("secret_key", TaintCategory.SENSITIVE_DATA_LEAK, "Cryptographic master key", is_sensitive=True),
    TaintSourcePattern("auth_header", TaintCategory.SENSITIVE_DATA_LEAK, "Authorization bearer header", is_sensitive=True),
    TaintSourcePattern("credit_card", TaintCategory.SENSITIVE_DATA_LEAK, "Payment card information", is_sensitive=True),
)

# Standard Python Taint Sinks Catalog
DEFAULT_TAINT_SINKS: tuple[TaintSinkPattern, ...] = (
    # SQL Injection Sinks
    TaintSinkPattern("cursor.execute", TaintCategory.SQL_INJECTION, "CRITICAL", "CWE-89", "SQL Database Query Execution"),
    TaintSinkPattern("connection.execute", TaintCategory.SQL_INJECTION, "CRITICAL", "CWE-89", "Raw SQL Statement Execution"),
    TaintSinkPattern("session.execute", TaintCategory.SQL_INJECTION, "HIGH", "CWE-89", "ORM Session Raw Query Execution"),
    TaintSinkPattern("db.execute", TaintCategory.SQL_INJECTION, "CRITICAL", "CWE-89", "Database Engine Execution"),
    TaintSinkPattern("raw_sql", TaintCategory.SQL_INJECTION, "HIGH", "CWE-89", "Raw SQL evaluation"),
    # Command Injection Sinks
    TaintSinkPattern("subprocess.run", TaintCategory.COMMAND_INJECTION, "CRITICAL", "CWE-78", "Subprocess Execution"),
    TaintSinkPattern("subprocess.Popen", TaintCategory.COMMAND_INJECTION, "CRITICAL", "CWE-78", "Async Subprocess Invocation"),
    TaintSinkPattern("subprocess.call", TaintCategory.COMMAND_INJECTION, "CRITICAL", "CWE-78", "Process Invocation"),
    TaintSinkPattern("subprocess.check_output", TaintCategory.COMMAND_INJECTION, "CRITICAL", "CWE-78", "Process Output Extraction"),
    TaintSinkPattern("os.system", TaintCategory.COMMAND_INJECTION, "CRITICAL", "CWE-78", "Direct Shell Command Execution"),
    TaintSinkPattern("os.popen", TaintCategory.COMMAND_INJECTION, "CRITICAL", "CWE-78", "Piped Shell Command"),
    # Code Injection Sinks
    TaintSinkPattern("eval", TaintCategory.CODE_INJECTION, "CRITICAL", "CWE-94", "Dynamic Code Evaluation"),
    TaintSinkPattern("exec", TaintCategory.CODE_INJECTION, "CRITICAL", "CWE-94", "Dynamic Code Execution"),
    TaintSinkPattern("pickle.loads", TaintCategory.CODE_INJECTION, "CRITICAL", "CWE-502", "Unsafe Object Deserialization"),
    TaintSinkPattern("yaml.load", TaintCategory.CODE_INJECTION, "HIGH", "CWE-502", "Unsafe YAML Deserialization"),
    # Path Traversal Sinks
    TaintSinkPattern("open", TaintCategory.PATH_TRAVERSAL, "HIGH", "CWE-22", "File System Read/Write Access"),
    TaintSinkPattern("os.remove", TaintCategory.PATH_TRAVERSAL, "HIGH", "CWE-22", "File System Deletion"),
    TaintSinkPattern("shutil.rmtree", TaintCategory.PATH_TRAVERSAL, "CRITICAL", "CWE-22", "Directory Tree Removal"),
    # SSRF Sinks
    TaintSinkPattern("requests.get", TaintCategory.SSRF, "HIGH", "CWE-918", "Outbound HTTP Request (SSRF)"),
    TaintSinkPattern("requests.post", TaintCategory.SSRF, "HIGH", "CWE-918", "Outbound HTTP Post Request (SSRF)"),
    TaintSinkPattern("urllib.request.urlopen", TaintCategory.SSRF, "HIGH", "CWE-918", "Network Resource Fetch"),
    # Sensitive Data Leak Sinks (Logging)
    TaintSinkPattern("logger.info", TaintCategory.SENSITIVE_DATA_LEAK, "MEDIUM", "CWE-532", "Sensitive Information in System Log"),
    TaintSinkPattern("logger.error", TaintCategory.SENSITIVE_DATA_LEAK, "MEDIUM", "CWE-532", "Sensitive Information in Error Log"),
    TaintSinkPattern("logger.debug", TaintCategory.SENSITIVE_DATA_LEAK, "MEDIUM", "CWE-532", "Sensitive Information in Debug Log"),
    TaintSinkPattern("print", TaintCategory.SENSITIVE_DATA_LEAK, "LOW", "CWE-532", "Plaintext Print of Sensitive Variable"),
)


@dataclass
class TaintFlowStep:
    """Represents an atomic transition step in a taint propagation path."""

    step_number: int
    expression: str
    kind: str  # 'SOURCE', 'ASSIGN', 'ACCESS_PATH', 'ARGUMENT', 'PARAM_BIND', 'RETURNS_TO', 'SINK'
    location: SourceLocation | None = None
    description: str = ""


@dataclass
class TaintFlow:
    """Represents a validated end-to-end vulnerability flow from Source to Sink."""

    id: str
    category: TaintCategory
    severity: str
    cwe_id: str
    source_expr: str
    sink_target: str
    primary_location: SourceLocation
    steps: list[TaintFlowStep] = field(default_factory=list)
    summary: str = ""
    remediation_hint: str = ""
