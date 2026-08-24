"""Domain entities for Design Patterns metadata in Java."""

from __future__ import annotations

from dataclasses import dataclass, field

from pattern_detector.domain.value_objects import PatternCategory, PatternType


@dataclass(frozen=True)
class PatternDefinition:
    """Catalog metadata definition for a known software design pattern."""

    type: PatternType
    name: str
    category: PatternCategory
    description: str
    intent: str
    idiomatic_in_java: bool = True
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.type.value,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "intent": self.intent,
            "idiomatic_in_java": self.idiomatic_in_java,
            "tags": list(self.tags),
        }


PATTERN_CATALOG: dict[PatternType, PatternDefinition] = {
    PatternType.OBSERVER: PatternDefinition(
        type=PatternType.OBSERVER,
        name="Observer (Listeners / Pub-Sub)",
        category=PatternCategory.BEHAVIORAL,
        description="Defines a subscription mechanism to notify multiple subscriber objects about events.",
        intent="Keep decoupled components synchronized when state changes occur in the subject.",
        tags=["listener", "events", "pub-sub", "concurrency"],
    ),
    PatternType.STRATEGY: PatternDefinition(
        type=PatternType.STRATEGY,
        name="Strategy / Polymorphic Dispatch",
        category=PatternCategory.BEHAVIORAL,
        description="Defines a family of algorithms, encapsulates each one, and makes them interchangeable.",
        intent="Select algorithm implementation at runtime via polymorphic interfaces.",
        tags=["interfaces", "polymorphism", "dependency-injection"],
    ),
    PatternType.DECORATOR: PatternDefinition(
        type=PatternType.DECORATOR,
        name="Decorator / Wrapper",
        category=PatternCategory.STRUCTURAL,
        description="Attaches additional responsibilities to an object dynamically.",
        intent="Wrap objects with cross-cutting concerns (logging, auth, buffering, encryption) while conforming to the same interface.",
        tags=["wrapper", "delegation", "composition"],
    ),
    PatternType.CHAIN_OF_RESPONSIBILITY: PatternDefinition(
        type=PatternType.CHAIN_OF_RESPONSIBILITY,
        name="Chain of Responsibility / Pipeline",
        category=PatternCategory.BEHAVIORAL,
        description="Passes requests along a chain of potential handlers.",
        intent="Decouple request senders from receivers by allowing multiple handlers to process the request sequentially.",
        tags=["pipeline", "middleware", "handlers"],
    ),
    PatternType.SINGLETON: PatternDefinition(
        type=PatternType.SINGLETON,
        name="Singleton / Shared State",
        category=PatternCategory.CREATIONAL,
        description="Ensures a class has only one instance and provides a global access point to it.",
        intent="Control concurrent access to shared resources and ensure singular lifecycle.",
        tags=["singleton", "concurrency", "static-instance"],
    ),
    PatternType.FACTORY_METHOD: PatternDefinition(
        type=PatternType.FACTORY_METHOD,
        name="Factory Method / Constructor Wrapper",
        category=PatternCategory.CREATIONAL,
        description="Provides an interface for creating objects in a superclass or factory helper.",
        intent="Encapsulate object construction logic and decouple caller from concrete classes.",
        tags=["construction", "encapsulation", "factory"],
    ),
    PatternType.ADAPTER: PatternDefinition(
        type=PatternType.ADAPTER,
        name="Adapter / Interface Wrapper",
        category=PatternCategory.STRUCTURAL,
        description="Allows objects with incompatible interfaces to collaborate.",
        intent="Convert the interface of a class into another interface clients expect.",
        tags=["interop", "polymorphism", "wrapper"],
    ),
    PatternType.LIFECYCLE_COMPONENT: PatternDefinition(
        type=PatternType.LIFECYCLE_COMPONENT,
        name="Lifecycle Component",
        category=PatternCategory.ARCHITECTURAL,
        description="Manages stateful components with explicit start and stop lifecycles.",
        intent="Deterministic dependency lifecycle management (Spring Lifecycle, Component).",
        tags=["architecture", "lifecycle", "system"],
    ),
    PatternType.CIRCULAR_DEPENDENCY: PatternDefinition(
        type=PatternType.CIRCULAR_DEPENDENCY,
        name="Circular Dependency (Anti-Pattern)",
        category=PatternCategory.ARCHITECTURAL,
        description="Detects mutually dependent package cycles across modules.",
        intent="Enforce clean acyclic dependency graphs across packages and layers.",
        tags=["architecture", "dependency-graph", "modularity"],
    ),
    PatternType.ABSTRACT_FACTORY: PatternDefinition(
        type=PatternType.ABSTRACT_FACTORY,
        name="Abstract Factory",
        category=PatternCategory.CREATIONAL,
        description="Produces families of related or dependent objects without specifying their concrete classes.",
        intent="Provide an interface for creating families of related products.",
        tags=["creational", "factory", "family"],
    ),
    PatternType.BUILDER: PatternDefinition(
        type=PatternType.BUILDER,
        name="Builder",
        category=PatternCategory.CREATIONAL,
        description="Constructs complex objects step by step using method chaining.",
        intent="Separate the construction of a complex object from its representation.",
        tags=["creational", "step-by-step", "fluent"],
    ),
    PatternType.PROTOTYPE: PatternDefinition(
        type=PatternType.PROTOTYPE,
        name="Prototype",
        category=PatternCategory.CREATIONAL,
        description="Copies existing objects without making your code dependent on their classes.",
        intent="Specify the kinds of objects to create using a prototypical instance, creating new objects by copying this prototype.",
        tags=["creational", "cloning", "copy"],
    ),
    PatternType.BRIDGE: PatternDefinition(
        type=PatternType.BRIDGE,
        name="Bridge",
        category=PatternCategory.STRUCTURAL,
        description="Splits a large class or a set of closely related classes into two separate hierarchies.",
        intent="Decouple an abstraction from its implementation so that the two can vary independently.",
        tags=["structural", "abstraction", "implementation"],
    ),
    PatternType.COMPOSITE: PatternDefinition(
        type=PatternType.COMPOSITE,
        name="Composite",
        category=PatternCategory.STRUCTURAL,
        description="Composes objects into tree structures to represent part-whole hierarchies.",
        intent="Treat individual objects and compositions of objects uniformly.",
        tags=["structural", "tree", "part-whole"],
    ),
    PatternType.FACADE: PatternDefinition(
        type=PatternType.FACADE,
        name="Facade",
        category=PatternCategory.STRUCTURAL,
        description="Provides a simplified interface to a library, a framework, or any other complex set of classes.",
        intent="Provide a unified interface to a set of interfaces in a subsystem.",
        tags=["structural", "subsystem", "simplification"],
    ),
    PatternType.FLYWEIGHT: PatternDefinition(
        type=PatternType.FLYWEIGHT,
        name="Flyweight",
        category=PatternCategory.STRUCTURAL,
        description="Fits more objects into the available amount of RAM by sharing common parts of state between multiple objects.",
        intent="Use sharing to support large numbers of fine-grained objects efficiently.",
        tags=["structural", "caching", "memory-optimization"],
    ),
    PatternType.PROXY: PatternDefinition(
        type=PatternType.PROXY,
        name="Proxy",
        category=PatternCategory.STRUCTURAL,
        description="Provides a placeholder for another object to control access to it.",
        intent="Control access to an object, providing a surrogate or placeholder.",
        tags=["structural", "surrogate", "access-control"],
    ),
    PatternType.COMMAND: PatternDefinition(
        type=PatternType.COMMAND,
        name="Command / CQRS",
        category=PatternCategory.BEHAVIORAL,
        description="Turns a request into a stand-alone object that contains all information about the request.",
        intent="Encapsulate a request as an object, thereby letting you parameterize clients with different requests.",
        tags=["behavioral", "cqrs", "action"],
    ),
    PatternType.ITERATOR: PatternDefinition(
        type=PatternType.ITERATOR,
        name="Iterator",
        category=PatternCategory.BEHAVIORAL,
        description="Traverses elements of a collection without exposing its underlying representation.",
        intent="Provide a way to access the elements of an aggregate object sequentially without exposing its underlying representation.",
        tags=["behavioral", "traversal", "sequence"],
    ),
    PatternType.MEDIATOR: PatternDefinition(
        type=PatternType.MEDIATOR,
        name="Mediator",
        category=PatternCategory.BEHAVIORAL,
        description="Reduces chaotic dependencies between objects by forcing them to collaborate solely through a mediator.",
        intent="Define an object that encapsulates how a set of objects interact.",
        tags=["behavioral", "broker", "decoupling"],
    ),
    PatternType.MEMENTO: PatternDefinition(
        type=PatternType.MEMENTO,
        name="Memento",
        category=PatternCategory.BEHAVIORAL,
        description="Saves and restores the previous state of an object without revealing the details of its implementation.",
        intent="Capture and externalize an object's internal state so that the object can be restored to this state later.",
        tags=["behavioral", "snapshot", "undo"],
    ),
    PatternType.STATE: PatternDefinition(
        type=PatternType.STATE,
        name="State / Finite State Machine",
        category=PatternCategory.BEHAVIORAL,
        description="Allows an object to alter its behavior when its internal state changes.",
        intent="Allow an object to alter its behavior when its internal state changes.",
        tags=["behavioral", "fsm", "state-transitions"],
    ),
    PatternType.TEMPLATE_METHOD: PatternDefinition(
        type=PatternType.TEMPLATE_METHOD,
        name="Template Method",
        category=PatternCategory.BEHAVIORAL,
        description="Defines the skeleton of an algorithm in the superclass but lets subclasses override specific steps.",
        intent="Define the skeleton of an algorithm in an operation, deferring some steps to subclasses.",
        tags=["behavioral", "skeleton", "algorithm"],
    ),
    PatternType.VISITOR: PatternDefinition(
        type=PatternType.VISITOR,
        name="Visitor",
        category=PatternCategory.BEHAVIORAL,
        description="Separates algorithms from the objects on which they operate.",
        intent="Represent an operation to be performed on the elements of an object structure.",
        tags=["behavioral", "traversal", "double-dispatch"],
    ),
    PatternType.INTERPRETER: PatternDefinition(
        type=PatternType.INTERPRETER,
        name="Interpreter",
        category=PatternCategory.BEHAVIORAL,
        description="Given a language, define a representation for its grammar along with an interpreter that uses the representation.",
        intent="Define a representation for a grammar and an interpreter to evaluate sentences in the language.",
        tags=["behavioral", "grammar", "evaluation"],
    ),
    PatternType.SINGLE_RESPONSIBILITY: PatternDefinition(
        type=PatternType.SINGLE_RESPONSIBILITY,
        name="Single Responsibility Principle (SRP)",
        category=PatternCategory.PRINCIPLE,
        description="A class should have one, and only one, reason to change.",
        intent="Keep classes cohesive and avoid God Object anti-patterns mixing multiple disparate concerns.",
        tags=["solid", "srp", "cohesion", "clean-code"],
    ),
    PatternType.OPEN_CLOSED: PatternDefinition(
        type=PatternType.OPEN_CLOSED,
        name="Open/Closed Principle (OCP)",
        category=PatternCategory.PRINCIPLE,
        description="Software entities should be open for extension, but closed for modification.",
        intent="Design polymorphic extension points and eliminate fragile type-testing instanceof/switch cascades.",
        tags=["solid", "ocp", "polymorphism", "extensibility"],
    ),
    PatternType.LISKOV_SUBSTITUTION: PatternDefinition(
        type=PatternType.LISKOV_SUBSTITUTION,
        name="Liskov Substitution Principle (LSP)",
        category=PatternCategory.PRINCIPLE,
        description="Subtypes must be substitutable for their base types without altering system correctness.",
        intent="Prevent derived classes from throwing UnsupportedOperationException or breaking base type contracts.",
        tags=["solid", "lsp", "subtyping", "correctness"],
    ),
    PatternType.INTERFACE_SEGREGATION: PatternDefinition(
        type=PatternType.INTERFACE_SEGREGATION,
        name="Interface Segregation Principle (ISP)",
        category=PatternCategory.PRINCIPLE,
        description="Clients should not be forced to depend upon interfaces that they do not use.",
        intent="Favor many client-specific fine-grained role interfaces over one monolithic fat interface.",
        tags=["solid", "isp", "interfaces", "role-design"],
    ),
    PatternType.DEPENDENCY_INVERSION: PatternDefinition(
        type=PatternType.DEPENDENCY_INVERSION,
        name="Dependency Inversion Principle (DIP)",
        category=PatternCategory.PRINCIPLE,
        description="High-level modules should not depend on low-level modules; both should depend on abstractions.",
        intent="Decouple core domain logic from infrastructure details via interface injection.",
        tags=["solid", "dip", "dependency-injection", "inversion-of-control"],
    ),
    PatternType.COMPOSITION_OVER_INHERITANCE: PatternDefinition(
        type=PatternType.COMPOSITION_OVER_INHERITANCE,
        name="Composition Over Inheritance",
        category=PatternCategory.PRINCIPLE,
        description="Favor object composition (has-a) and delegation over class inheritance (is-a).",
        intent="Avoid fragile base class problems and rigid inheritance hierarchies exceeding depth 2.",
        tags=["clean-code", "composition", "delegation", "modularity"],
    ),
    PatternType.LAW_OF_DEMETER: PatternDefinition(
        type=PatternType.LAW_OF_DEMETER,
        name="Law of Demeter (LoD)",
        category=PatternCategory.PRINCIPLE,
        description="Principle of Least Knowledge: each unit should have only limited knowledge about other units.",
        intent="Eliminate train-wreck chained calls (a.getB().getC().doWork()) that create tight structural coupling.",
        tags=["clean-code", "law-of-demeter", "coupling", "encapsulation"],
    ),
    PatternType.HIGH_COHESION_LOW_COUPLING: PatternDefinition(
        type=PatternType.HIGH_COHESION_LOW_COUPLING,
        name="High Cohesion & Low Coupling",
        category=PatternCategory.PRINCIPLE,
        description="Maximize the focus and relatedness of internal elements while minimizing inter-module dependencies.",
        intent="Ensure modular, testable, and independently evolvable packages and classes.",
        tags=["clean-code", "cohesion", "coupling", "modularity"],
    ),
    PatternType.KISS: PatternDefinition(
        type=PatternType.KISS,
        name="Keep It Simple, Stupid (KISS)",
        category=PatternCategory.PRINCIPLE,
        description="Most systems work best if they are kept simple rather than made complicated.",
        intent="Detect overly complex parameter lists, deep nesting, and over-engineered logic.",
        tags=["clean-code", "kiss", "simplicity", "complexity"],
    ),
    PatternType.DRY: PatternDefinition(
        type=PatternType.DRY,
        name="Don't Repeat Yourself (DRY)",
        category=PatternCategory.PRINCIPLE,
        description="Every piece of knowledge must have a single, unambiguous, authoritative representation.",
        intent="Avoid duplicate structural signatures and boilerplate across classes.",
        tags=["clean-code", "dry", "maintainability"],
    ),
}
