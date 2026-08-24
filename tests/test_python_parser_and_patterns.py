"""Tests for Python AST Parser and Python Pattern Detection."""

from pattern_detector.adapters.outbound.python_ast.py_parser_adapter import PyParserAdapter
from pattern_detector.domain.rules import get_default_rules
from pattern_detector.domain.services.pattern_detector import PatternDetectorService
from pattern_detector.domain.value_objects import PatternType


def test_python_parser_extracts_classes_and_interfaces() -> None:
    py_code = """
from abc import ABC, abstractmethod

class IOrderProcessor(ABC):
    @abstractmethod
    def process_order(self, order_id: int) -> None:
        pass

    @abstractmethod
    def validate(self, customer_id: str) -> bool:
        pass

class StandardOrderProcessor(IOrderProcessor):
    def process_order(self, order_id: int) -> None:
        print(f"Processing order: {order_id}")

    def validate(self, customer_id: str) -> bool:
        return bool(customer_id)
"""

    adapter = PyParserAdapter()
    model = adapter.parse_sources({"order_processor.py": py_code})

    assert "order_processor" in model.namespaces
    ns = model.namespaces["order_processor"]
    assert "IOrderProcessor" in ns.protocols
    assert "StandardOrderProcessor" in ns.records
    assert "IOrderProcessor" in ns.records["StandardOrderProcessor"].implemented_protocols


def test_python_pattern_detection_strategy_and_composite() -> None:
    py_code = """
from abc import ABC, abstractmethod
from typing import List

class IGraphic(ABC):
    @abstractmethod
    def render(self) -> None:
        pass

class Circle(IGraphic):
    def render(self) -> None:
        print("Circle")

class CanvasContainer(IGraphic):
    def __init__(self) -> None:
        self.children: List[IGraphic] = []

    def render(self) -> None:
        for g in self.children:
            g.render()
"""

    adapter = PyParserAdapter()
    model = adapter.parse_sources({"graphic.py": py_code})
    detector = PatternDetectorService(rules=get_default_rules())
    report = detector.detect_all(model)

    assert report.total_detections_count >= 1
    pattern_types = [d.pattern_type for d in report.detections]
    assert PatternType.STRATEGY in pattern_types or PatternType.COMPOSITE in pattern_types or PatternType.OPEN_CLOSED in pattern_types
