"""Domain pattern and engineering principles rules exports and default registry."""

from pattern_detector.domain.rules.abstract_factory_rule import AbstractFactoryRule
from pattern_detector.domain.rules.adapter_rule import AdapterPatternRule
from pattern_detector.domain.rules.base import BasePatternRule, PatternRule
from pattern_detector.domain.rules.bridge_rule import BridgePatternRule
from pattern_detector.domain.rules.builder_rule import BuilderPatternRule
from pattern_detector.domain.rules.chain_of_responsibility_rule import ChainOfResponsibilityRule
from pattern_detector.domain.rules.circular_dependency_rule import CircularDependencyRule
from pattern_detector.domain.rules.cohesion_coupling_rule import CohesionCouplingRule
from pattern_detector.domain.rules.command_rule import CommandPatternRule
from pattern_detector.domain.rules.composite_rule import CompositePatternRule
from pattern_detector.domain.rules.composition_over_inheritance_rule import CompositionOverInheritanceRule
from pattern_detector.domain.rules.decorator_rule import DecoratorPatternRule
from pattern_detector.domain.rules.dip_rule import DependencyInversionRule
from pattern_detector.domain.rules.dry_rule import DryRule
from pattern_detector.domain.rules.facade_rule import FacadePatternRule
from pattern_detector.domain.rules.factory_rule import FactoryPatternRule
from pattern_detector.domain.rules.flyweight_rule import FlyweightPatternRule
from pattern_detector.domain.rules.interpreter_rule import InterpreterPatternRule
from pattern_detector.domain.rules.isp_rule import InterfaceSegregationRule
from pattern_detector.domain.rules.iterator_rule import IteratorPatternRule
from pattern_detector.domain.rules.kiss_rule import KissRule
from pattern_detector.domain.rules.law_of_demeter_rule import LawOfDemeterRule
from pattern_detector.domain.rules.lifecycle_rule import LifecycleComponentPatternRule
from pattern_detector.domain.rules.lsp_rule import LiskovSubstitutionRule
from pattern_detector.domain.rules.mediator_rule import MediatorPatternRule
from pattern_detector.domain.rules.memento_rule import MementoPatternRule
from pattern_detector.domain.rules.observer_rule import ObserverPatternRule
from pattern_detector.domain.rules.ocp_rule import OpenClosedPrincipleRule
from pattern_detector.domain.rules.prototype_rule import PrototypePatternRule
from pattern_detector.domain.rules.proxy_rule import ProxyPatternRule
from pattern_detector.domain.rules.singleton_rule import SingletonPatternRule
from pattern_detector.domain.rules.srp_rule import SingleResponsibilityRule
from pattern_detector.domain.rules.state_rule import StatePatternRule
from pattern_detector.domain.rules.strategy_rule import StrategyPatternRule
from pattern_detector.domain.rules.template_method_rule import TemplateMethodRule
from pattern_detector.domain.rules.visitor_rule import VisitorPatternRule


def get_default_rules() -> list[PatternRule]:
    """Return an instantiated list of all built-in pattern and principle detection rules."""
    return [
        # GoF Patterns (23) & Architecture (2)
        ObserverPatternRule(),
        StrategyPatternRule(),
        DecoratorPatternRule(),
        SingletonPatternRule(),
        FactoryPatternRule(),
        AdapterPatternRule(),
        LifecycleComponentPatternRule(),
        ChainOfResponsibilityRule(),
        CircularDependencyRule(),
        TemplateMethodRule(),
        CommandPatternRule(),
        BuilderPatternRule(),
        FacadePatternRule(),
        ProxyPatternRule(),
        StatePatternRule(),
        FlyweightPatternRule(),
        AbstractFactoryRule(),
        PrototypePatternRule(),
        CompositePatternRule(),
        BridgePatternRule(),
        IteratorPatternRule(),
        MediatorPatternRule(),
        MementoPatternRule(),
        VisitorPatternRule(),
        InterpreterPatternRule(),
        # SOLID & Clean Code Principles (10)
        SingleResponsibilityRule(),
        OpenClosedPrincipleRule(),
        LiskovSubstitutionRule(),
        InterfaceSegregationRule(),
        DependencyInversionRule(),
        CompositionOverInheritanceRule(),
        LawOfDemeterRule(),
        CohesionCouplingRule(),
        KissRule(),
        DryRule(),
    ]


__all__ = [
    "AbstractFactoryRule",
    "AdapterPatternRule",
    "BasePatternRule",
    "BridgePatternRule",
    "BuilderPatternRule",
    "ChainOfResponsibilityRule",
    "CircularDependencyRule",
    "CohesionCouplingRule",
    "CommandPatternRule",
    "CompositePatternRule",
    "CompositionOverInheritanceRule",
    "DecoratorPatternRule",
    "DependencyInversionRule",
    "DryRule",
    "FacadePatternRule",
    "FactoryPatternRule",
    "FlyweightPatternRule",
    "InterfaceSegregationRule",
    "InterpreterPatternRule",
    "IteratorPatternRule",
    "KissRule",
    "LawOfDemeterRule",
    "LifecycleComponentPatternRule",
    "LiskovSubstitutionRule",
    "MediatorPatternRule",
    "MementoPatternRule",
    "ObserverPatternRule",
    "OpenClosedPrincipleRule",
    "PatternRule",
    "PrototypePatternRule",
    "ProxyPatternRule",
    "SingleResponsibilityRule",
    "SingletonPatternRule",
    "StatePatternRule",
    "StrategyPatternRule",
    "TemplateMethodRule",
    "VisitorPatternRule",
    "get_default_rules",
]
