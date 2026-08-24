"""Edge Cases False Positives Test Suite for Python Design Patterns & SOLID Principles.

Validates that complex Python idioms (Context Managers, Generators, Async Coroutines,
Properties, Custom Exceptions, Enums, UserDict/UserList, Pydantic DTOs, and Decorator functions)
do not produce false positive detections.
"""

from pattern_detector.adapters.outbound.python_ast.py_parser_adapter import PyParserAdapter
from pattern_detector.domain.rules import get_default_rules
from pattern_detector.domain.services.pattern_detector import PatternDetectorService
from pattern_detector.domain.value_objects import ConfidenceLevel, PatternType


def _scan_snippet(code_map: dict[str, str]):
    adapter = PyParserAdapter()
    model = adapter.parse_sources(code_map)
    detector = PatternDetectorService(rules=get_default_rules())
    return detector.detect_all(model)


def test_context_manager_not_flagged_as_state_or_lifecycle() -> None:
    code = """
class TimerContext:
    def __init__(self, name: str) -> None:
        self.name = name

    def __enter__(self) -> "TimerContext":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass
"""
    report = _scan_snippet({"timer_context.py": code})
    assert report.total_detections_count == 0


def test_python_dunder_iter_and_next_not_flagged_as_singleton_or_state() -> None:
    code = """
class CountdownIterator:
    def __init__(self, start: int) -> None:
        self.current = start

    def __iter__(self) -> "CountdownIterator":
        return self

    def __next__(self) -> int:
        if self.current <= 0:
            raise StopIteration
        val = self.current
        self.current -= 1
        return val
"""
    report = _scan_snippet({"countdown.py": code})
    assert report.total_detections_count == 0


def test_user_dict_subclass_not_flagged_as_strategy_or_adapter() -> None:
    code = """
from collections import UserDict

class CaseInsensitiveDict(UserDict):
    def __getitem__(self, key: str):
        return super().__getitem__(key.lower())

    def __setitem__(self, key: str, value):
        super().__setitem__(key.lower(), value)

    def __contains__(self, key: object) -> bool:
        if isinstance(key, str):
            return super().__contains__(key.lower())
        return False
"""
    report = _scan_snippet({"case_dict.py": code})
    assert report.total_detections_count == 0


def test_pydantic_from_dict_and_to_dict_not_flagged_as_factory_or_prototype() -> None:
    code = """
class UserModel:
    def __init__(self, username: str, email: str) -> None:
        self.username = username
        self.email = email

    @classmethod
    def from_dict(cls, data: dict) -> "UserModel":
        return cls(username=data["username"], email=data["email"])

    def to_dict(self) -> dict:
        return {"username": self.username, "email": self.email}
"""
    report = _scan_snippet({"user_model.py": code})
    assert report.total_detections_count == 0


def test_non_fluent_mutating_setters_not_flagged_as_builder() -> None:
    code = """
class AccountProfile:
    def __init__(self) -> None:
        self.status = "PENDING"
        self.tier = "STANDARD"

    def set_status(self, new_status: str) -> None:
        self.status = new_status

    def set_tier(self, new_tier: str) -> None:
        self.tier = new_tier
"""
    report = _scan_snippet({"account_profile.py": code})
    builder_detections = [
        d
        for d in report.detections
        if d.pattern_type == PatternType.BUILDER
        and d.confidence.level in (ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH)
    ]
    assert len(builder_detections) == 0


def test_http_notification_client_not_flagged_as_observer_subject() -> None:
    code = """
class EmailNotificationClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def notify_admin(self, subject: str, body: str) -> None:
        pass

    def subscribe_newsletter(self, email: str) -> None:
        pass
"""
    report = _scan_snippet({"email_client.py": code})
    observer_detections = [
        d
        for d in report.detections
        if d.pattern_type == PatternType.OBSERVER
        and d.confidence.level in (ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH)
    ]
    assert len(observer_detections) == 0


def test_custom_exception_subclasses_not_flagged_as_lsp_violation() -> None:
    code = """
class ValidationError(ValueError):
    def __init__(self, message: str, code: int = 400) -> None:
        super().__init__(message)
        self.code = code
"""
    report = _scan_snippet({"exceptions.py": code})
    assert report.total_detections_count == 0


def test_properties_and_descriptors_not_flagged_as_srp_god_class() -> None:
    code = """
class TemperatureReading:
    def __init__(self, celsius: float = 0.0) -> None:
        self._celsius = celsius

    @property
    def celsius(self) -> float:
        return self._celsius

    @celsius.setter
    def celsius(self, val: float) -> None:
        if val < -273.15:
            raise ValueError("Absolute zero violation")
        self._celsius = val

    @property
    def fahrenheit(self) -> float:
        return self._celsius * 9 / 5 + 32
"""
    report = _scan_snippet({"temperature.py": code})
    assert report.total_detections_count == 0


def test_async_context_manager_not_flagged_as_state_machine() -> None:
    code = """
class AsyncDatabaseSession:
    def __init__(self, conn_str: str) -> None:
        self.conn_str = conn_str
        self.is_connected = False

    async def __aenter__(self) -> "AsyncDatabaseSession":
        self.is_connected = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.is_connected = False
"""
    report = _scan_snippet({"async_session.py": code})
    assert report.total_detections_count == 0


def test_enum_and_intenum_not_flagged_as_strategy_or_composite() -> None:
    code = """
from enum import Enum, IntEnum

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class LogLevel(IntEnum):
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
"""
    report = _scan_snippet({"enums.py": code})
    assert report.total_detections_count == 0


def test_function_decorator_wrapper_not_flagged_as_gof_decorator_class() -> None:
    code = """
import functools
import time

def measure_latency(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        print(f"{func.__name__} took {duration:.4f}s")
        return result
    return wrapper
"""
    report = _scan_snippet({"timing_decorator.py": code})
    decorator_detections = [
        d
        for d in report.detections
        if d.pattern_type == PatternType.DECORATOR
        and d.confidence.level in (ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH)
    ]
    assert len(decorator_detections) == 0


def test_generator_stream_not_flagged_as_iterator_pattern() -> None:
    code = """
from typing import Iterator

def read_large_file(file_path: str, chunk_size: int = 1024) -> Iterator[str]:
    with open(file_path, "r", encoding="utf-8") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk
"""
    report = _scan_snippet({"generator.py": code})
    assert report.total_detections_count == 0
