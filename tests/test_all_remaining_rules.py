"""Tests for design pattern rules on Python source code."""

from pattern_detector.adapters.outbound.python_ast.py_parser_adapter import PyParserAdapter
from pattern_detector.domain.rules.abstract_factory_rule import AbstractFactoryRule
from pattern_detector.domain.rules.bridge_rule import BridgePatternRule
from pattern_detector.domain.rules.composite_rule import CompositePatternRule
from pattern_detector.domain.rules.iterator_rule import IteratorPatternRule
from pattern_detector.domain.rules.mediator_rule import MediatorPatternRule
from pattern_detector.domain.value_objects import PatternType


def test_abstract_factory_rule_python() -> None:
    code = """
from abc import ABC, abstractmethod

class IButton(ABC):
    pass

class ICheckbox(ABC):
    pass

class WinButton(IButton):
    pass

class WinCheckbox(ICheckbox):
    pass

class IGUIFactory(ABC):
    @abstractmethod
    def create_button(self) -> IButton:
        pass

    @abstractmethod
    def create_checkbox(self) -> ICheckbox:
        pass

class WinFactory(IGUIFactory):
    def create_button(self) -> IButton:
        return WinButton()

    def create_checkbox(self) -> ICheckbox:
        return WinCheckbox()
"""
    model = PyParserAdapter().parse_sources({"gui_factory.py": code})
    detections = AbstractFactoryRule().detect(model)
    assert len(detections) >= 1
    assert detections[0].pattern_type == PatternType.ABSTRACT_FACTORY
    assert detections[0].target_name == "IGUIFactory"


def test_composite_rule_python() -> None:
    code = """
from abc import ABC, abstractmethod
from typing import List

class IGraphic(ABC):
    @abstractmethod
    def draw(self) -> None:
        pass

class Dot(IGraphic):
    def draw(self) -> None:
        pass

class CompoundGraphic(IGraphic):
    def __init__(self) -> None:
        self.children: List[IGraphic] = []

    def draw(self) -> None:
        for g in self.children:
            g.draw()
"""
    model = PyParserAdapter().parse_sources({"graphic.py": code})
    detections = CompositePatternRule().detect(model)
    assert len(detections) >= 1
    assert detections[0].pattern_type == PatternType.COMPOSITE
    assert detections[0].target_name == "IGraphic"


def test_bridge_rule_python() -> None:
    code = """
from abc import ABC, abstractmethod

class IDatabaseDriver(ABC):
    @abstractmethod
    def execute_query(self, sql: str) -> None:
        pass

class DatabaseService:
    def __init__(self, driver: IDatabaseDriver) -> None:
        self.driver = driver

    def run(self, sql: str) -> None:
        self.driver.execute_query(sql)
"""
    model = PyParserAdapter().parse_sources({"bridge.py": code})
    detections = BridgePatternRule().detect(model)
    assert len(detections) >= 1
    assert detections[0].pattern_type == PatternType.BRIDGE


def test_iterator_rule_python() -> None:
    code = """
from abc import ABC, abstractmethod

class ICustomIterator(ABC):
    @abstractmethod
    def has_next(self) -> bool:
        pass

    @abstractmethod
    def next(self) -> str:
        pass
"""
    model = PyParserAdapter().parse_sources({"custom_iterator.py": code})
    detections = IteratorPatternRule().detect(model)
    assert len(detections) >= 1
    assert detections[0].pattern_type == PatternType.ITERATOR


def test_mediator_rule_python() -> None:
    code = """
from abc import ABC, abstractmethod

class IEventBroker(ABC):
    @abstractmethod
    def publish(self, topic: str, msg: str) -> None:
        pass

    @abstractmethod
    def subscribe(self, topic: str) -> None:
        pass

class MessageHub(IEventBroker):
    def publish(self, topic: str, msg: str) -> None:
        pass

    def subscribe(self, topic: str) -> None:
        pass
"""
    model = PyParserAdapter().parse_sources({"mediator.py": code})
    detections = MediatorPatternRule().detect(model)
    assert len(detections) >= 1
    assert any(d.pattern_type == PatternType.MEDIATOR for d in detections)
