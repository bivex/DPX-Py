"""Tests for design pattern rules on Python source code."""

from pattern_detector.adapters.outbound.python_ast.py_parser_adapter import PyParserAdapter
from pattern_detector.domain.rules.lifecycle_rule import LifecycleComponentPatternRule
from pattern_detector.domain.rules.singleton_rule import SingletonPatternRule
from pattern_detector.domain.rules.strategy_rule import StrategyPatternRule
from pattern_detector.domain.value_objects import PatternType


def test_strategy_pattern_python() -> None:
    code = """
from abc import ABC, abstractmethod
from typing import List

class ISortStrategy(ABC):
    @abstractmethod
    def sort(self, data: List[int]) -> None:
        pass

class QuickSort(ISortStrategy):
    def sort(self, data: List[int]) -> None:
        pass

class MergeSort(ISortStrategy):
    def sort(self, data: List[int]) -> None:
        pass
"""
    model = PyParserAdapter().parse_sources({"sort_strategy.py": code})
    detections = StrategyPatternRule().detect(model)
    assert len(detections) >= 1
    assert detections[0].pattern_type == PatternType.STRATEGY
    assert detections[0].target_name == "ISortStrategy"


def test_singleton_pattern_python() -> None:
    code = """
from typing import Optional

class AppConfig:
    _instance: Optional["AppConfig"] = None

    @classmethod
    def get_instance(cls) -> "AppConfig":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
"""
    model = PyParserAdapter().parse_sources({"app_config.py": code})
    detections = SingletonPatternRule().detect(model)
    assert len(detections) >= 1
    assert any(d.pattern_type == PatternType.SINGLETON for d in detections)


def test_lifecycle_component_pattern_python() -> None:
    code = """
from abc import ABC, abstractmethod

class ILifecycle(ABC):
    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

class HttpServerComponent(ILifecycle):
    def start(self) -> None:
        print("Starting server")

    def stop(self) -> None:
        print("Stopping server")
"""
    model = PyParserAdapter().parse_sources({"lifecycle.py": code})
    detections = LifecycleComponentPatternRule().detect(model)
    assert len(detections) >= 1
    assert detections[0].pattern_type == PatternType.LIFECYCLE_COMPONENT
