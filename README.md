# ⚡ DPX-Py: Pattern Scanner, Software Architecture Analyzer & Data Flow Engine for Python

> **Hexagonal Architecture (Ports & Adapters) + Domain-Driven Design (DDD)** static analysis, pattern detection and high-performance data flow engine for **Python (3.8 - 3.13+)** powered by native Python **AST parsing**, **SciTools Understand-parity Data Flow Out / In Analysis**, **Cytoscape.js Graph Engine**, and **Semantic UI (Fomantic-UI)** interactive dashboards.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat&logo=python)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Hexagonal%20%2B%20DDD-brightgreen.svg?style=flat)]()
[![Parser](https://img.shields.io/badge/Parser-Python%20AST%20(Native)-red.svg?style=flat)](https://docs.python.org/3/library/ast.html)
[![Visualizer](https://img.shields.io/badge/Graph%20Engine-Cytoscape.js%20%2B%20Dagre-0284c7.svg?style=flat)](https://js.cytoscape.org/)
[![UI Theme](https://img.shields.io/badge/UI-Semantic%20UI%20(Fomantic)-35bdb2.svg?style=flat)](https://fomantic-ui.com/)
[![Tests](https://img.shields.io/badge/Tests-74%20passed%20(100%25)-success.svg?style=flat)]()
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
                    │   • Semantic UI Pattern Scanner HTML Dashboard         │
                    │   • Cytoscape.js & Semantic UI Data Flow HTML Formatter│
                    │   • GitHub-Flavored Markdown Formatter & Repository    │
                    │   • OASIS SARIF v2.1.0 Formatter (GitHub Code Scanning)│
                    │   • Token-Efficient LLM Prompt Context Formatter       │
                    └────────────────────────────────────────────────────────┘
```

---

## ✨ Key Capabilities

### 1. 🔍 All 23 Gang of Four (GoF) Design Patterns Detected in Python:
* **Creational**: Abstract Factory, Builder (Fluent method chaining returning `self`), Factory Method, Prototype, Singleton (decorator & `_instance` / `get_instance()` idioms).
* **Structural**: Adapter, Bridge, Composite (hierarchical trees with component interfaces), Decorator, Facade, Flyweight, Proxy.
* **Behavioral**: Chain of Responsibility, Command, Interpreter, Iterator, Mediator, Memento, Observer (Subject classes, subscriber lists, `subscribe`/`notify` lifecycles), State, Strategy (polymorphic Protocol/ABC implementations), Template Method, Visitor.

### 2. 🛡️ 10 SOLID Principles & Clean Code Rules:
* **Single Responsibility (SRP)**: God Class detection ($\ge 15$ methods mixing multiple domains).
* **Open/Closed (OCP)**: Type inspection cascades (`isinstance()`, `type() is ...`) vs. polymorphic Protocol/ABC dispatch.
* **Liskov Substitution (LSP)**: Subclasses refusing parent contract with `raise NotImplementedError` / `raise TypeError`.
* **Interface Segregation (ISP)**: Fat Protocols/ABCs ($\ge 8$ methods) forcing unnecessary obligations.
* **Dependency Inversion (DIP)**: Direct instantiation of concrete infrastructure classes vs. Protocol/ABC injection.
* **Law of Demeter (LoD)**: Train wreck dot chaining (`order.get_customer().get_profile().get_address().get_postal_code()`).
* **KISS**: Long parameter lists ($\ge 5$ parameters) & high cyclomatic complexity.
* **DRY**: Duplicate method bodies across modules.
* **High Cohesion / Low Coupling**: High fan-out import coupling ($\ge 10$).
* **Circular Dependency**: Inter-module import loop detection via Tarjan's Strongly Connected Components (SCC).

### 3. 🌲 High-Performance Data Flow Engine (SciTools Understand Parity):
* **Data Flow OUT (Forward Slicing)**: Traces downstream mutation propagation, reach, and blast radius.
* **Data Flow IN (Backward Slicing)**: Traces upstream data origins, writers, and dependencies.
* **Relationship Paths**: Computes exact shortest propagation paths between any two variables.
* **High-Speed Execution**: BFS graph expansion with built-in damping and Python builtins filtering (<0.40s on large repositories).

### 4. 🎨 Modern Semantic UI (Fomantic-UI) & Cytoscape.js Dashboards:
* **Pattern Scanner Dashboard**: Semantic UI Dark Theme with interactive KPI stats, category filter pills, Evidence Trail heuristic inspector, and instant live search.
* **Data Flow Visualizer**: Powered by **Cytoscape.js 3.30 (Canvas/WebGL)** + **Dagre / Cola / Concentric** layout engines with neighbor highlighting, node inspector, High-DPI PNG export, and JSON export.

### 5. 💡 Pattern & Data Flow Coder Insights:
* Combines detected patterns with live data flow metrics to deliver concrete, actionable developer hints with Python code suggestions.

### 6. 📤 Multi-Format Export:
* Rich CLI Console tables, JSON, Markdown, OASIS SARIF v2.1.0 (GitHub Code Scanning integration), interactive HTML dashboards, and token-dense `--llm` XML context.

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
# 1. Scan a Python project or file for patterns and SOLID violations
uv run pattern-detector scan /path/to/python/project

# 2. Scan and export interactive Semantic UI HTML dashboard & SARIF report
uv run pattern-detector scan /path/to/python/project --html reports/patterns_dashboard.html --sarif reports/scan.sarif

# 3. Trace Data Flow OUT (Forward Slice) for a specific variable
uv run pattern-detector dataflow user_session --path /path/to/python/project

# 4. Generate full project Data Flow Matrix & Cytoscape.js HTML Visualizer
uv run pattern-detector dataflow --all --path /path/to/python/project --html reports/dataflow_dashboard.html

# 5. Generate Pattern-Dataflow Coder Insights
uv run pattern-detector insights /path/to/python/project

# 6. Generate token-efficient LLM prompt context
uv run pattern-detector scan /path/to/python/project --llm
```

---

## 🧪 Running Tests & Quality Checks

```bash
# Run pytest test suite (54 unit & integration tests)
uv run pytest -v

# Type checking with strict mypy (85 source files)
uv run mypy src tests

# Code linting & formatting with ruff
uv run ruff check .
```

---

## 📊 Benchmark & Performance

| Analysis Step | Targets | Execution Time | Output Size |
|---|:---:|:---:|:---:|
| **Pattern Scanner (35 Rules)** | 51 modules | **0.031s** | 518 KB (HTML) |
| **Data Flow Analysis (1,600+ vars)** | Entire Codebase | **0.405s** | 1.76 MB (HTML) |
| **Cytoscape.js Rendering** | Complex Graphs | **0 ms lag (60 FPS)** | Canvas / WebGL |

---

## 🌐 The DPX Suite Family

Cross-language architectural static analysis across all modern programming languages:

| Repository | Language / Ecosystem | Primary Paradigms & Focus |
|---|---|---|
| **[`DPX-Yul`](https://github.com/bivex/DPX-Yul)** | **Yul / EVM Assembly** (0.8.x - 0.8.28+ / Cancun) | **Memory Management, Storage Packing, Transient Storage (EIP-1153), GoF 23** |
| **[`DPX-Cairo`](https://github.com/bivex/DPX-Cairo)** | **Cairo** (Cairo 1.0 - 2.8+ / Starknet) | **Components, Storage Mapping, Syscalls, Account Abstraction, Upgrades, GoF 23** |
| **[`DPX-Move`](https://github.com/bivex/DPX-Move)** | **Move** (Move 2024 / Aptos / Sui) | **Linear Resources, Abilities, Sui Objects, Hot Potato, Prover, GoF 23** |
| **[`DPX-Lua`](https://github.com/bivex/DPX-Lua)** | **Lua / Luau** (5.1 - 5.4 / LuaJIT) | **Metatable OOP, Coroutines, LuaJIT FFI, GameDev (Roblox/Neovim), GoF 23** |
| **[`DPX-Solidity`](https://github.com/bivex/DPX-Solidity)** | **Solidity** (0.8.x - 0.8.28+) | **EVM Gas Optimization, Proxies, CEI Reentrancy, Yul, GoF 23, Security** |
| **[`DPX-Zig`](https://github.com/bivex/DPX-Zig)** | **Zig** (0.11 - 0.14+) | **Comptime Generics, Allocator RAII, Defer Cleanup, SIMD, GoF 23** |
| **[`DPX-Gleam`](https://github.com/bivex/DPX-Gleam)** | **Gleam** (1.0 - 1.8+) | **Type-Safe OTP Actors, Algebraic Data Types, Railway Monads, GoF 23** |
| **[`DPX-Mojo`](https://github.com/bivex/DPX-Mojo)** | **Mojo** (24.x - 25.x+) | **SIMD Vectorization, Ownership, Memory Safety, GoF 23, AI Acceleration** |
| **[`DPX-Julia`](https://github.com/bivex/DPX-Julia)** | **Julia** (1.6 - 1.11+) | **Multiple Dispatch, Holy Traits, Metaprogramming, Tasks, GoF 23** |
| **[`DPX-Kotlin`](https://github.com/bivex/DPX-Kotlin)** | **Kotlin** (1.8 - 2.0+) | **Coroutines, Flow, Jetpack Compose, Multiplatform, GoF 23** |
| **[`DPX-Swift`](https://github.com/bivex/DPX-Swift)** | **Swift** (5.5 - 6.0+) | **Protocol-Oriented, Actor Concurrency, SwiftUI, ARC Safety** |
| **[`DPX-CSharp`](https://github.com/bivex/DPX-CSharp)** | **C#** (10 - 13 / .NET 8-9) | **Clean Architecture, CQRS MediatR, Channel Pipelines** |
| **[`DPX-TypeScript`](https://github.com/bivex/DPX-TypeScript)** | **TypeScript / JavaScript** | **Hexagonal DI, Decorator Meta, Reactive Streams, React/NestJS** |
| **[`DPX-Rust`](https://github.com/bivex/DPX-Rust)** | **Rust** (Edition 2021/2024) | **Zero-Cost Abstractions, RAII Lifetimes, Typestate Pattern** |
| **[`DPX-Go`](https://github.com/bivex/DPX-Go)** | **Go** (1.18 - 1.24+) | **Goroutine Channels, CSP Concurrency, Pipeline Streaming** |
| **[`DPX-Py`](https://github.com/bivex/DPX-Py)** | **Python** (3.8 - 3.13+) | **Multi-Paradigm Hexagonal, Data Flow Engine, AsyncIO** |
| **[`DPX-Php`](https://github.com/bivex/DPX-Php)** | **PHP** (8.1 - 8.4+) | **Attribute-driven DDD, Fiber Concurrency, Laravel/Symfony** |
| **[`DPX-Haskell`](https://github.com/bivex/DPX-Haskell)** | **Haskell** (GHC 9.2 - 9.12+) | **Category Theory, Monad Transformers, Free Monads, Optics** |
| **[`DPX-OCaml`](https://github.com/bivex/DPX-OCaml)** | **OCaml** (4.14 - 5.3+ Multicore) | **Functor Modules, Effect Handlers, GADTs, Railway Monads** |
| **[`DPX-Elixir`](https://github.com/bivex/DPX-Elixir)** | **Elixir** (OTP 25 - 27+) | **GenServer, DynamicSupervisor, Actor Fault Tolerance** |
| **[`DPX-Erlang`](https://github.com/bivex/DPX-Erlang)** | **Erlang/OTP** (24 - 27+) | **OTP Behaviors, Supervision Trees, Message Passing** |
| **[`DPX-C`](https://github.com/bivex/DPX-C)** | **C** (C99 - C23) | **Opaque Structs, VTables, MISRA/CERT Safety, Arena Allocators** |
| **[`DPX-Cpp`](https://github.com/bivex/DPX-Cpp)** | **C++** (C++14 - C++20) | **CRTP, Policy-Based Design, RAII Memory Safety, ANTLR4 AST** |
| **[`DPX-Java`](https://github.com/bivex/DPX-Java)** | **Java** (17 - 23+) | **Virtual Threads, Spring Boot / Jakarta EE, GoF Patterns** |
| **[`DPX`](https://github.com/bivex/DPX)** | **Clojure** / Meta Engine | **Pure Functional, Multimethods, Homoiconic Macro Architecture** |
---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
