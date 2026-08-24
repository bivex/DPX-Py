"""Comprehensive False Positives Test Suite for DPX-Py.

Verifies that ordinary, standard Python idioms (dataclasses, DTOs, standard library functions,
built-in collections, operator methods, vector math, linked list data structures,
and pure utility functions) do not produce false positive detections for Design Patterns
or SOLID Principle violations.
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


def test_plain_pure_math_and_string_utilities_have_zero_detections() -> None:
    code = """
class MathUtils:
    @staticmethod
    def add(a: int, b: int) -> int:
        return a + b

    @staticmethod
    def multiply(x: int, y: int) -> int:
        return x * y

    @staticmethod
    def factorial(n: int) -> int:
        if n <= 1:
            return 1
        return n * MathUtils.factorial(n - 1)
"""
    report = _scan_snippet({"math_utils.py": code})
    assert report.total_detections_count == 0


def test_dto_with_many_getters_and_setters_not_flagged_as_srp_god_object() -> None:
    code = """
from dataclasses import dataclass

@dataclass
class CustomerProfileDto:
    id: str
    first_name: str
    last_name: str
    email: str
    phone_number: str
    street_address: str
    city: str
    postal_code: str
    country: str
    status: str
"""
    report = _scan_snippet({"customer_dto.py": code})
    srp_detections = [d for d in report.detections if d.pattern_type == PatternType.SINGLE_RESPONSIBILITY]
    assert len(srp_detections) == 0


def test_standard_operator_equals_not_flagged_as_ocp_violation() -> None:
    code = """
class MoneyValue:
    def __init__(self, amount: float, currency: str) -> None:
        self.amount = amount
        self.currency = currency

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MoneyValue):
            return False
        return self.amount == other.amount and self.currency == other.currency
"""
    report = _scan_snippet({"money_value.py": code})
    ocp_detections = [d for d in report.detections if d.pattern_type == PatternType.OPEN_CLOSED]
    assert len(ocp_detections) == 0


def test_service_instantiating_list_or_dict_not_flagged_as_dip_violation() -> None:
    code = """
from typing import List

class ItemListingService:
    def generate_summary(self) -> List[str]:
        result = []
        result.append("Item A")
        result.append("Item B")
        return result
"""
    report = _scan_snippet({"item_service.py": code})
    dip_detections = [d for d in report.detections if d.pattern_type == PatternType.DEPENDENCY_INVERSION]
    assert len(dip_detections) == 0


def test_simple_record_getters_not_flagged_as_dry_duplicate_code() -> None:
    code_a = """
class UserEntity:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id

    def get_id(self) -> str:
        return self.user_id
"""
    code_b = """
class ProductEntity:
    def __init__(self, product_id: str) -> None:
        self.product_id = product_id

    def get_id(self) -> str:
        return self.product_id
"""
    report = _scan_snippet({
        "user_entity.py": code_a,
        "product_entity.py": code_b,
    })
    dry_detections = [d for d in report.detections if d.pattern_type == PatternType.DRY]
    assert len(dry_detections) == 0


def test_string_helpers_with_make_or_create_name_not_flagged_as_factory() -> None:
    code = """
class StringHelpers:
    @staticmethod
    def make_uppercase(s: str) -> str:
        return s.upper()

    @staticmethod
    def create_slug(title: str) -> str:
        return title.lower().replace(" ", "-")
"""
    report = _scan_snippet({"string_helpers.py": code})
    factory_detections = [
        d for d in report.detections
        if d.pattern_type == PatternType.FACTORY_METHOD and d.confidence.level in (ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH)
    ]
    assert len(factory_detections) == 0


def test_immutable_vector2d_math_not_flagged_as_builder() -> None:
    code = """
class Vector2D:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def add(self, other: "Vector2D") -> "Vector2D":
        return Vector2D(self.x + other.x, self.y + other.y)

    def scale(self, factor: float) -> "Vector2D":
        return Vector2D(self.x * factor, self.y * factor)
"""
    report = _scan_snippet({"vector.py": code})
    builder_detections = [
        d for d in report.detections
        if d.pattern_type == PatternType.BUILDER and d.confidence.level in (ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH)
    ]
    assert len(builder_detections) == 0


def test_class_with_normal_cache_not_flagged_as_singleton() -> None:
    code = """
class ImageCache:
    def __init__(self) -> None:
        self.cache: dict[str, bytes] = {}
        self.hits: int = 0
        self.misses: int = 0

    def get_image(self, key: str) -> bytes | None:
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None
"""
    report = _scan_snippet({"image_cache.py": code})
    singleton_detections = [
        d for d in report.detections
        if d.pattern_type == PatternType.SINGLETON and d.confidence.level in (ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH)
    ]
    assert len(singleton_detections) == 0


def test_linked_list_node_not_flagged_as_chain_of_responsibility() -> None:
    code = """
class ListNode:
    def __init__(self, val: int = 0, next_node: "ListNode | None" = None) -> None:
        self.val = val
        self.next = next_node

    def get_length(self) -> int:
        count = 0
        curr: ListNode | None = self
        while curr:
            count += 1
            curr = curr.next
        return count
"""
    report = _scan_snippet({"list_node.py": code})
    cor_detections = [
        d for d in report.detections
        if d.pattern_type == PatternType.CHAIN_OF_RESPONSIBILITY and d.confidence.level in (ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH)
    ]
    assert len(cor_detections) == 0


def test_binary_search_tree_not_flagged_as_composite_pattern() -> None:
    code = """
class TreeNode:
    def __init__(self, key: int) -> None:
        self.key = key
        self.left: "TreeNode | None" = None
        self.right: "TreeNode | None" = None

    def insert(self, val: int) -> None:
        if val < self.key:
            if self.left is None:
                self.left = TreeNode(val)
            else:
                self.left.insert(val)
        else:
            if self.right is None:
                self.right = TreeNode(val)
            else:
                self.right.insert(val)
"""
    report = _scan_snippet({"bst.py": code})
    composite_detections = [
        d for d in report.detections
        if d.pattern_type == PatternType.COMPOSITE and d.confidence.level in (ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH)
    ]
    assert len(composite_detections) == 0


def test_simple_event_logger_not_flagged_as_observer_subject() -> None:
    code = """
class EventLogger:
    def __init__(self) -> None:
        self.logs: list[str] = []

    def log(self, message: str) -> None:
        self.logs.append(message)

    def flush(self) -> None:
        self.logs.clear()
"""
    report = _scan_snippet({"logger.py": code})
    observer_detections = [
        d for d in report.detections
        if d.pattern_type == PatternType.OBSERVER and d.confidence.level in (ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH)
    ]
    assert len(observer_detections) == 0


def test_batch_script_with_run_method_not_flagged_as_command_pattern() -> None:
    code = """
class DatabaseMigrationScript:
    def __init__(self, db_url: str) -> None:
        self.db_url = db_url

    def run(self) -> None:
        # Simple standalone script execution, no abstract Command interface
        print(f"Connecting to {self.db_url}")
"""
    report = _scan_snippet({"migration.py": code})
    command_detections = [
        d for d in report.detections
        if d.pattern_type == PatternType.COMMAND and d.confidence.level in (ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH)
    ]
    assert len(command_detections) == 0


def test_url_crawler_with_visit_method_not_flagged_as_visitor_pattern() -> None:
    code = """
class WebCrawler:
    def __init__(self) -> None:
        self.visited_urls: set[str] = set()

    def visit(self, url: str) -> None:
        if url not in self.visited_urls:
            self.visited_urls.add(url)
"""
    report = _scan_snippet({"crawler.py": code})
    visitor_detections = [
        d for d in report.detections
        if d.pattern_type == PatternType.VISITOR and d.confidence.level in (ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH)
    ]
    assert len(visitor_detections) == 0


def test_lsp_rule_and_ast_extractor_not_flagged_as_lsp_violation() -> None:
    code = """
from abc import ABC, abstractmethod

class BaseDetector(ABC):
    @abstractmethod
    def detect(self, text: str) -> list[str]:
        pass

class ConcreteLspRule(BaseDetector):
    def detect(self, text: str) -> list[str]:
        # String checking keywords, NOT raising an exception
        keywords = ("notimplemented", "unsupported", "logic_error")
        results = [k for k in keywords if k in text]
        return results

class NodeVisitorBase:
    def visit(self, node: object) -> None:
        pass

class AstExtractor(NodeVisitorBase):
    def _extract_method(self, node: object) -> str:
        # Method returning extracted name, not throwing
        return "method_name"
"""
    report = _scan_snippet({"detector.py": code})
    lsp_detections = [
        d for d in report.detections
        if d.pattern_type == PatternType.LISKOV_SUBSTITUTION
    ]
    assert len(lsp_detections) == 0

