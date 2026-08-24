"""Tests for Python Module Dependency Graph and Circular Dependency Detection."""

from pattern_detector.adapters.outbound.python_ast.py_parser_adapter import PyParserAdapter
from pattern_detector.domain.rules.circular_dependency_rule import CircularDependencyRule
from pattern_detector.domain.value_objects import PatternType


def test_circular_dependency_detection_python() -> None:
    code_a = """
import beta

class AlphaService:
    def __init__(self) -> None:
        self.beta = beta.BetaService()
"""
    code_b = """
import alpha

class BetaService:
    def __init__(self) -> None:
        self.alpha = alpha.AlphaService()
"""

    adapter = PyParserAdapter()
    model = adapter.parse_sources({
        "alpha.py": code_a,
        "beta.py": code_b,
    })

    cycles = model.find_circular_dependencies()
    assert len(cycles) == 1
    assert set(cycles[0]) == {"alpha", "beta"}

    rule = CircularDependencyRule()
    detections = rule.detect(model)
    assert len(detections) == 1
    assert detections[0].pattern_type == PatternType.CIRCULAR_DEPENDENCY
    assert detections[0].confidence.score >= 0.80
