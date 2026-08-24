"""Unit tests for SOLID Principles, Clean Code, Coupling & Cohesion Rules for Python."""

from pattern_detector.adapters.outbound.python_ast.py_parser_adapter import PyParserAdapter
from pattern_detector.domain.rules.cohesion_coupling_rule import CohesionCouplingRule
from pattern_detector.domain.rules.composition_over_inheritance_rule import CompositionOverInheritanceRule
from pattern_detector.domain.rules.dip_rule import DependencyInversionRule
from pattern_detector.domain.rules.dry_rule import DryRule
from pattern_detector.domain.rules.isp_rule import InterfaceSegregationRule
from pattern_detector.domain.rules.kiss_rule import KissRule
from pattern_detector.domain.rules.law_of_demeter_rule import LawOfDemeterRule
from pattern_detector.domain.rules.lsp_rule import LiskovSubstitutionRule
from pattern_detector.domain.rules.ocp_rule import OpenClosedPrincipleRule
from pattern_detector.domain.rules.srp_rule import SingleResponsibilityRule
from pattern_detector.domain.value_objects import PatternCategory, PatternType


def test_srp_god_object_violation() -> None:
    code = """
class MegaGodManager:
    def save_to_database(self) -> None: pass
    def delete_from_database(self) -> None: pass
    def query_database(self) -> None: pass
    def handle_http_request(self) -> None: pass
    def get_http_endpoint(self) -> None: pass
    def serialize_to_json(self) -> None: pass
    def parse_xml(self) -> None: pass
    def authenticate_user(self) -> None: pass
    def calculate_taxes(self) -> None: pass
    def compute_discounts(self) -> None: pass
    def process_order(self) -> None: pass
    def validate_payment(self) -> None: pass
"""
    model = PyParserAdapter().parse_sources({"mega_god_manager.py": code})
    detections = SingleResponsibilityRule().detect(model)
    assert len(detections) >= 1
    assert detections[0].pattern_type == PatternType.SINGLE_RESPONSIBILITY
    assert detections[0].pattern_category == PatternCategory.PRINCIPLE


def test_ocp_dynamic_cast_cascade_violation() -> None:
    code = """
class ShapeDrawer:
    def draw_shape(self, shape: object) -> None:
        if isinstance(shape, Circle):
            print("Drawing circle")
        elif isinstance(shape, Square):
            print("Drawing square")
        elif isinstance(shape, Triangle):
            print("Drawing triangle")
"""
    model = PyParserAdapter().parse_sources({"shape_drawer.py": code})
    detections = OpenClosedPrincipleRule().detect(model)
    assert len(detections) >= 1
    assert detections[0].pattern_type == PatternType.OPEN_CLOSED
    assert "isinstance" in detections[0].evidences[0].description or "type" in detections[0].evidences[0].description


def test_lsp_unsupported_operation_violation() -> None:
    code = """
from abc import ABC, abstractmethod

class IReadOnlyList(ABC):
    @abstractmethod
    def get(self, index: int) -> int:
        pass

    @abstractmethod
    def add(self, item: int) -> None:
        pass

class ImmutableListImpl(IReadOnlyList):
    def get(self, index: int) -> int:
        return 0

    def add(self, item: int) -> None:
        raise NotImplementedError("Immutable list cannot be modified")
"""
    model = PyParserAdapter().parse_sources({"immutable_list.py": code})
    detections = LiskovSubstitutionRule().detect(model)
    assert len(detections) >= 1
    assert detections[0].pattern_type == PatternType.LISKOV_SUBSTITUTION


def test_isp_fat_interface_violation() -> None:
    code = """
from abc import ABC, abstractmethod

class IMonolithicWorker(ABC):
    @abstractmethod
    def code(self) -> None: pass
    @abstractmethod
    def test(self) -> None: pass
    @abstractmethod
    def deploy(self) -> None: pass
    @abstractmethod
    def manage_infrastructure(self) -> None: pass
    @abstractmethod
    def review_budget(self) -> None: pass
    @abstractmethod
    def design_graphics(self) -> None: pass
    @abstractmethod
    def recruit_employees(self) -> None: pass
    @abstractmethod
    def handle_customer_support(self) -> None: pass
    @abstractmethod
    def clean_office(self) -> None: pass
"""
    model = PyParserAdapter().parse_sources({"monolithic_worker.py": code})
    detections = InterfaceSegregationRule().detect(model)
    assert len(detections) >= 1
    assert detections[0].pattern_type == PatternType.INTERFACE_SEGREGATION


def test_dip_concrete_instantiation_violation() -> None:
    code = """
class OrderProcessingService:
    def process_order(self) -> None:
        repo = MySqlDatabaseRepository()
        repo.save_order()
"""
    model = PyParserAdapter().parse_sources({"order_service.py": code})
    detections = DependencyInversionRule().detect(model)
    assert len(detections) >= 1
    assert detections[0].pattern_type == PatternType.DEPENDENCY_INVERSION


def test_composition_over_inheritance_deep_hierarchy() -> None:
    code = """
class BaseEntity: pass
class AuditableEntity(BaseEntity): pass
class VersionedEntity(AuditableEntity): pass
class ConcreteUserEntity(VersionedEntity): pass
"""
    model = PyParserAdapter().parse_sources({"hierarchy.py": code})
    detections = CompositionOverInheritanceRule().detect(model)
    assert len(detections) >= 1
    assert detections[0].pattern_type == PatternType.COMPOSITION_OVER_INHERITANCE


def test_law_of_demeter_train_wreck_violation() -> None:
    code = """
class ShippingService:
    def calculate_shipping(self, order: object) -> None:
        zip_code = order.get_customer().get_address().get_location().get_postal_code()
        print(f"Zip: {zip_code}")
"""
    model = PyParserAdapter().parse_sources({"shipping_service.py": code})
    detections = LawOfDemeterRule().detect(model)
    assert len(detections) >= 1
    assert detections[0].pattern_type == PatternType.LAW_OF_DEMETER


def test_kiss_long_parameter_list_violation() -> None:
    code = """
class ComplexCalculator:
    def compute_metrics(self, a: int, b: int, name: str, rate: float, flag: bool, mode: str, ctx: object) -> None:
        print("Computing")
"""
    model = PyParserAdapter().parse_sources({"complex_calculator.py": code})
    detections = KissRule().detect(model)
    assert len(detections) >= 1
    assert detections[0].pattern_type == PatternType.KISS


def test_dry_duplicate_code_violation() -> None:
    code_a = """
class AlphaProcessor:
    def calculate_standard_discount(self, price: float, count: int) -> float:
        base = price * count
        if base > 100.0:
            return base * 0.85
        return base * 0.95
"""
    code_b = """
class BetaProcessor:
    def compute_partner_discount(self, price: float, count: int) -> float:
        base = price * count
        if base > 100.0:
            return base * 0.85
        return base * 0.95
"""
    model = PyParserAdapter().parse_sources(
        {
            "alpha_processor.py": code_a,
            "beta_processor.py": code_b,
        }
    )
    detections = DryRule().detect(model)
    assert len(detections) >= 1
    assert detections[0].pattern_type == PatternType.DRY


def test_cohesion_coupling_high_fan_out() -> None:
    code_hub = """
import mod1
import mod2
import mod3
import mod4

class GlobalOrchestrator:
    pass
"""
    model = PyParserAdapter().parse_sources(
        {
            "hub.py": code_hub,
            "mod1.py": "class Mod1: pass",
            "mod2.py": "class Mod2: pass",
            "mod3.py": "class Mod3: pass",
            "mod4.py": "class Mod4: pass",
        }
    )
    detections = CohesionCouplingRule().detect(model)
    assert len(detections) >= 1
    assert detections[0].pattern_type == PatternType.HIGH_COHESION_LOW_COUPLING
