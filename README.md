# ⚡ DPX-Py: Pattern Scanner, Software Architecture Analyzer & Data Flow Engine for Python

> **Hexagonal Architecture (Ports & Adapters) + Domain-Driven Design (DDD)** static analysis, pattern detection and data flow engine for **Python (3.8 - 3.13+)** powered by native Python **AST parsing**, **SciTools Understand-parity Data Flow Out / In Analysis**, and **Architectural Coder Insights**.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat&logo=python)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Hexagonal%20%2B%20DDD-brightgreen.svg?style=flat)]()
[![Parser](https://img.shields.io/badge/Parser-Python%20AST%20(Native)-red.svg?style=flat)](https://docs.python.org/3/library/ast.html)
[![Tests](https://img.shields.io/badge/Tests-54%20passed%20(100%25)-success.svg?style=flat)]()
[![Code Style](https://img.shields.io/badge/Linter-Ruff%20%26%20Mypy%20Strict-black.svg?style=flat)]()
[![Rules](https://img.shields.io/badge/Supported%20Rules-35%20(23%20GoF%20%2B%2010%20SOLID%2FPrinciples%20%2B%202%20Arch)-orange.svg?style=flat)]()
[![SARIF](https://img.shields.io/badge/SARIF-v2.1.0%20OASIS-blue.svg?style=flat)]()
[![Data Flow](https://img.shields.io/badge/Data%20Flow-Understand%20Parity%20(Out%20%2F%20In)-purple.svg?style=flat)]()

---

## 🏛 Architecture Overview

The system strictly follows **Domain-Driven Design (DDD)** and **Hexagonal Architecture (Ports & Adapters)**. The domain layer has **zero knowledge** of Python AST implementation details, filesystem, or CLI frameworks.

```text
                    ┌────────────────────────────────────────────────────────┐
                    │                    Driving Adapters                    │
                    │                                                        │
                    │   Typer + Rich CLI         /       Python SDK API      │
                    └───────────────────────────┬────────────────────────────┘
                                                │
                                                ▼
                    ┌────────────────────────────────────────────────────────┐
                    │                   Application Layer                    │
                    │                                                        │
                    │     ScanningService (Pipeline Coordinator & Use Cases) │
                    └───────────────────────────┬────────────────────────────┘
                                                │
                                      ┌─────────▼─────────┐
                                      │    DOMAIN CORE    │
                                      │                   │
                                      │  CodeModel        │
                                      │  35 AnalysisRules │
                                      │  DataFlowService  │
                                      │  PatternInsights  │
                                      │  Confidence Model │
                                      │  Evidence Trail   │
                                      │  Dependency Graph │
                                      └─────────┬─────────┘
                                                │
                    ┌───────────────────────────▼────────────────────────────┐
                    │                      Ports / SPI                       │
                    │                                                        │
                    │   Inbound:  ScannerPort, DetectorPort, DataFlowPort    │
                    │   Outbound: ParserPort, SourceProviderPort,            │
                    │             ResultRepositoryPort, ReportFormatterPort  │
                    └───────────────────────────┬────────────────────────────┘
                                                │
                    ┌───────────────────────────▼────────────────────────────┐
                    │                    Driven Adapters                     │
                    │                                                        │
                    │   • Native Python AST Parser (PyParserAdapter)         │
                    │   • FileSystem Source Provider (.py, .pyi recursive)   │
                    │   • Interactive HTML Dashboard Formatter & Repository  │
                    │   • GitHub-Flavored Markdown Formatter & Repository    │
                    │   • OASIS SARIF v2.1.0 Formatter (GitHub Code Scanning)│
                    │   • Token-Efficient LLM Prompt Context Formatter       │
                    │   • Vis.js Interactive Graph & Matrix HTML Formatter   │
                    └────────────────────────────────────────────────────────┘
```

---

## ✨ Key Capabilities

1. **All 23 Gang of Four (GoF) Design Patterns Detected in Python**:
   - **Creational**: Abstract Factory, Builder, Factory Method, Prototype, Singleton.
   - **Structural**: Adapter, Bridge, Composite, Decorator, Facade, Flyweight, Proxy.
   - **Behavioral**: Chain of Responsibility, Command, Interpreter, Iterator, Mediator, Memento, Observer, State, Strategy, Template Method, Visitor.
2. **10 SOLID Principles & Clean Code Rules**:
   - **Single Responsibility (SRP)**: God Class detection ($\ge 15$ methods).
   - **Open/Closed (OCP)**: Type inspection cascades (`isinstance()`, `type() is ...`) vs. polymorphic Protocol/ABC dispatch.
   - **Liskov Substitution (LSP)**: Subclasses refusing parent contract with `raise NotImplementedError`.
   - **Interface Segregation (ISP)**: Fat Protocols/ABCs ($\ge 8$ methods) forcing unnecessary method implementations.
   - **Dependency Inversion (DIP)**: Direct instantiation of concrete infrastructure classes vs. Protocol/ABC injection.
   - **Law of Demeter (LoD)**: Train wreck dot chaining (`order.get_customer().get_profile().get_address().get_postal_code()`).
   - **KISS**: Long parameter lists ($\ge 5$ parameters) & high cyclomatic complexity.
   - **DRY**: Duplicate method bodies across modules.
   - **High Cohesion / Low Coupling**: High fan-out import coupling ($\ge 10$).
   - **Circular Dependency**: Inter-module import loop detection.
3. **Data Flow Engine (SciTools Understand Parity)**:
   - **Data Flow OUT (Forward Slicing)**: Traces downstream mutation propagation, reach, and blast radius.
   - **Data Flow IN (Backward Slicing)**: Traces upstream data origins, writers, and dependencies.
   - **Relationship Paths**: Finds exact shortest propagation path between two variables.
   - **Mermaid & Vis.js Dashboards**: Interactive physics-based graph visualizations.
4. **Pattern & Data Flow Coder Insights**:
   - Combines detected patterns with live data flow metrics to deliver concrete, actionable developer hints with Python code suggestions.
5. **Multi-Format Export**:
   - Rich CLI Console tables, JSON, Markdown, OASIS SARIF v2.1.0 (GitHub Code Scanning), interactive HTML dashboards, and token-dense `--llm` XML context.

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/bivex/DPX-Py.git
cd DPX-Py

# Sync virtualenv and dependencies with uv
uv sync
```

### CLI Usage

```bash
# Scan a Python project or file
uv run pattern-detector scan /path/to/python/project

# Scan and export interactive HTML dashboard & SARIF report
uv run pattern-detector scan /path/to/python/project --html reports/dashboard.html --sarif reports/scan.sarif

# Trace Data Flow OUT for a variable
uv run pattern-detector dataflow user_session --path /path/to/python/project

# Trace all variables matrix across project
uv run pattern-detector dataflow --all --path /path/to/python/project --html reports/dataflow.html

# Generate Pattern-Dataflow Coder Insights
uv run pattern-detector insights /path/to/python/project

# Generate token-efficient LLM prompt context
uv run pattern-detector scan /path/to/python/project --llm
```

---

## 🧪 Running Tests

```bash
# Run pytest test suite (54 unit & integration tests)
uv run pytest -v

# Type checking with strict mypy
uv run mypy src tests

# Code linting & formatting with ruff
uv run ruff check .
```

---

## 📄 License

MIT License. Designed and crafted with Clean Architecture & Domain-Driven Design principles.
