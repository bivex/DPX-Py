"""Comprehensive False Positives Test Suite for DPX-Py.

Verifies that ordinary, standard Python idioms (dataclasses, DTOs, standard library functions,
built-in collections, operator methods, and pure utility functions)
do not produce false positive detections for Design Patterns or SOLID Principle violations.
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
    # Pure standard utilities must not trigger any false detections
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
