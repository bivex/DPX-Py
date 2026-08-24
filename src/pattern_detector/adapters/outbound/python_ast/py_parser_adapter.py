"""Python AST Parser Adapter implementing ParserPort using standard library `ast`."""

from __future__ import annotations

import ast
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from pattern_detector.domain.code_model import (
    CodeModel,
    FunctionModel,
    MethodSignature,
    NamespaceModel,
    ProtocolModel,
    RecordModel,
    StateModel,
)
from pattern_detector.domain.value_objects import SourceLocation
from pattern_detector.ports.outbound import ParserPort

_PYTHON_BUILTINS_AND_KEYWORDS = frozenset(
    {
        "self",
        "cls",
        "None",
        "True",
        "False",
        "int",
        "str",
        "float",
        "bool",
        "list",
        "dict",
        "set",
        "tuple",
        "bytes",
        "object",
        "type",
        "id",
        "len",
        "range",
        "enumerate",
        "zip",
        "map",
        "filter",
        "print",
        "sum",
        "min",
        "max",
        "any",
        "all",
        "isinstance",
        "issubclass",
        "hasattr",
        "getattr",
        "setattr",
        "delattr",
        "super",
        "property",
        "staticmethod",
        "classmethod",
        "abstractmethod",
        "ABC",
        "Protocol",
        "Any",
        "Optional",
        "Union",
        "List",
        "Dict",
        "Set",
        "Tuple",
        "Callable",
        "Iterable",
        "Iterator",
        "Sequence",
        "Mapping",
        "dataclass",
        "field",
        "open",
        "round",
        "abs",
        "sorted",
        "reversed",
        "iter",
        "next",
        "repr",
        "format",
        "dir",
        "vars",
        "eval",
        "exec",
        "Exception",
        "ValueError",
        "TypeError",
        "KeyError",
        "IndexError",
        "AttributeError",
        "NotImplementedError",
        "RuntimeError",
        "StopIteration",
    }
)


class _PythonAstExtractor(ast.NodeVisitor):
    """AST visitor extracting structural domain models from Python source code."""

    def __init__(self, file_path: str, source_code: str) -> None:
        self.file_path = file_path
        self.source_code = source_code
        self.module_name = self._compute_module_name(file_path)

        self.imports: list[str] = []
        self.requires: list[str] = []
        self.protocols: dict[str, ProtocolModel] = {}
        self.records: dict[str, RecordModel] = {}
        self.functions: dict[str, FunctionModel] = {}
        self.states: dict[str, StateModel] = {}

        self._current_class: str | None = None
        self._class_fields: dict[str, list[str]] = {}
        self._class_methods: dict[str, list[FunctionModel]] = {}
        self._class_pure_methods: dict[str, list[MethodSignature]] = {}
        self._class_bases: dict[str, list[str]] = {}

    def _compute_module_name(self, file_path: str) -> str:
        if not file_path:
            return "global"
        base = os.path.splitext(os.path.basename(file_path))[0]
        if base == "__init__":
            parent = os.path.basename(os.path.dirname(file_path))
            return parent or "root"
        return base

    def _get_loc(self, node: ast.AST) -> SourceLocation:
        lineno = getattr(node, "lineno", 1)
        col = getattr(node, "col_offset", 0) + 1
        return SourceLocation(file_path=self.file_path, line=lineno, column=col)

    def _extract_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            val_name = self._extract_name(node.value)
            return f"{val_name}.{node.attr}" if val_name else node.attr
        elif isinstance(node, ast.Call):
            return self._extract_name(node.func)
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return ""

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.name
            self.imports.append(name)
            base_mod = name.split(".")[0]
            if base_mod not in self.requires:
                self.requires.append(base_mod)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = node.module or ""
        self.imports.append(mod)
        base_mod = mod.split(".")[0] if mod else ""
        if base_mod and base_mod not in self.requires:
            self.requires.append(base_mod)
        for alias in node.names:
            self.imports.append(f"{mod}.{alias.name}" if mod else alias.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        class_name = node.name
        loc = self._get_loc(node)
        prev_class = self._current_class
        self._current_class = class_name

        self._class_fields[class_name] = []
        self._class_methods[class_name] = []
        self._class_pure_methods[class_name] = []

        bases = self._extract_class_bases(node)
        self._class_bases[class_name] = bases

        decorator_names = [self._extract_name(d) for d in node.decorator_list]
        is_singleton_decorated = any("singleton" in d.lower() for d in decorator_names)

        self._visit_class_body(class_name, node)

        methods = self._class_methods.get(class_name, [])
        pure_methods = self._class_pure_methods.get(class_name, [])
        fields = self._class_fields.get(class_name, [])

        is_abstract = self._is_abstract_class(bases, pure_methods, node)

        record = RecordModel(
            name=class_name,
            namespace=self.module_name,
            location=loc,
            fields=fields,
            implemented_protocols=bases,
            methods=methods,
            is_type=is_abstract,
            docstring=ast.get_docstring(node) or "",
        )
        self.records[class_name] = record

        self._register_protocol_if_needed(class_name, is_abstract, methods, loc, node)
        self._register_singleton_state_if_needed(class_name, is_singleton_decorated, fields, methods, loc)

        self._current_class = prev_class

    def _extract_class_bases(self, node: ast.ClassDef) -> list[str]:
        bases: list[str] = []
        for base_expr in node.bases:
            b_name = self._extract_name(base_expr)
            if b_name:
                bases.append(b_name)
        return bases

    def _extract_pure_methods(self, methods: list[Any]) -> list[MethodSignature]:
        return [MethodSignature(name=m.name.split(".")[-1], location=m.location) for m in methods if m.is_abstract]

    def _extract_class_body_items(self, class_name: str, node: ast.ClassDef) -> None:
        for item in node.body:
            if isinstance(item, (ast.Assign, ast.AnnAssign)):
                self._extract_class_attribute(class_name, item)
            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._extract_method(class_name, item)

    def _visit_class_body(self, class_name: str, node: ast.ClassDef) -> None:
        for item in node.body:
            if isinstance(item, (ast.Assign, ast.AnnAssign)):
                self._extract_class_attribute(class_name, item)
            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._extract_method(class_name, item)

    def _is_abstract_class(self, bases: list[str], pure_methods: list[Any], node: ast.ClassDef) -> bool:
        if any(b in ("ABC", "abc.ABC", "Protocol", "typing.Protocol", "typing_extensions.Protocol") for b in bases):
            return True
        if len(pure_methods) > 0:
            return True
        for kw in node.keywords:
            if kw.arg == "metaclass" and "ABCMeta" in self._extract_name(kw.value):
                return True
        return False

    def _is_interface_name(self, class_name: str) -> bool:
        return class_name.startswith("I") and len(class_name) > 2 and class_name[1].isupper()

    def _register_protocol_if_needed(
        self,
        class_name: str,
        is_abstract: bool,
        methods: list[Any],
        loc: SourceLocation,
        node: ast.ClassDef,
    ) -> None:
        if is_abstract or (self._is_interface_name(class_name) and len(methods) > 0):
            pure_methods = self._extract_pure_methods(methods)
            signatures = (
                pure_methods
                if pure_methods
                else [MethodSignature(name=m.name.split(".")[-1], location=m.location) for m in methods]
            )
            self.protocols[class_name] = ProtocolModel(
                name=class_name,
                namespace=self.module_name,
                location=loc,
                methods=signatures,
                docstring=ast.get_docstring(node) or "",
            )

    def _register_singleton_state_if_needed(
        self,
        class_name: str,
        is_singleton_decorated: bool,
        fields: list[str],
        methods: list[Any],
        loc: SourceLocation,
    ) -> None:
        has_instance_field = any(f in ("_instance", "_instances", "instance", "__instance") for f in fields)
        has_new_override = any(m.name.endswith(".__new__") or m.name == "__new__" for m in methods)
        has_get_instance = any("get_instance" in m.name.lower() or "getinstance" in m.name.lower() for m in methods)

        if is_singleton_decorated or (has_instance_field and (has_new_override or has_get_instance)):
            self.states[f"{class_name}._instance"] = StateModel(
                name=f"{class_name}._instance",
                namespace=self.module_name,
                location=loc,
                kind="atom",
                is_once=True,
                is_dynamic=True,
            )

    def _extract_class_attribute(self, class_name: str, node: ast.Assign | ast.AnnAssign) -> None:
        targets: list[ast.AST] = list(node.targets) if isinstance(node, ast.Assign) else [node.target]
        for t in targets:
            name = self._extract_name(t)
            if name:
                self._class_fields[class_name].append(name)

    def _extract_method(self, class_name: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        fn_name = node.name
        qualified_name = f"{class_name}.{fn_name}"
        loc = self._get_loc(node)
        params = self._extract_method_params(node)

        if self._is_method_abstract(node):
            self._class_pure_methods[class_name].append(MethodSignature(name=fn_name, location=loc))

        calls, r_vars, w_vars, m_vars = self._analyze_body(node)
        self._update_class_init_fields(class_name, fn_name, w_vars)

        doc = ast.get_docstring(node) or ""
        body_stmts = "\n".join(ast.unparse(s) for s in node.body) if hasattr(ast, "unparse") else ""
        decorators = [self._extract_name(d) for d in node.decorator_list]
        is_abstract = self._is_method_abstract(node)
        fn_model = FunctionModel(
            name=qualified_name,
            namespace=self.module_name,
            location=loc,
            parameter_lists=[params],
            body_text=body_stmts,
            calls=sorted(set(calls)),
            reads_variables=sorted(set(r_vars)),
            writes_variables=sorted(set(w_vars)),
            modifies_variables=sorted(set(m_vars)),
            decorators=decorators,
            docstring=doc,
            is_private=fn_name.startswith("_") and not fn_name.startswith("__"),
            is_abstract=is_abstract,
        )

        self._class_methods[class_name].append(fn_model)
        self.functions[qualified_name] = fn_model

    def _extract_method_params(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        params = [arg.arg for arg in node.args.args if arg.arg not in ("self", "cls")]
        if node.args.vararg:
            params.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            params.append(f"**{node.args.kwarg.arg}")
        return params

    def _is_method_abstract(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        decorators = [self._extract_name(d) for d in node.decorator_list]
        return any("abstract" in d.lower() for d in decorators)

    def _update_class_init_fields(self, class_name: str, fn_name: str, w_vars: list[str]) -> None:
        if fn_name in ("__init__", "__post_init__"):
            for w in w_vars:
                if w.startswith("self."):
                    field_name = w.split(".", 1)[1]
                    if field_name not in self._class_fields[class_name]:
                        self._class_fields[class_name].append(field_name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if self._current_class is None:
            self._extract_free_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if self._current_class is None:
            self._extract_free_function(node)
        self.generic_visit(node)

    def _extract_free_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        fn_name = node.name
        loc = self._get_loc(node)
        params = [arg.arg for arg in node.args.args]
        if node.args.vararg:
            params.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            params.append(f"**{node.args.kwarg.arg}")

        calls, r_vars, w_vars, m_vars = self._analyze_body(node)
        doc = ast.get_docstring(node) or ""
        body_stmts = "\n".join(ast.unparse(s) for s in node.body) if hasattr(ast, "unparse") else ""
        decorators = [self._extract_name(d) for d in node.decorator_list]

        fn_model = FunctionModel(
            name=fn_name,
            namespace=self.module_name,
            location=loc,
            parameter_lists=[params],
            body_text=body_stmts,
            calls=sorted(set(calls)),
            reads_variables=sorted(set(r_vars)),
            writes_variables=sorted(set(w_vars)),
            modifies_variables=sorted(set(m_vars)),
            decorators=decorators,
            docstring=doc,
            is_private=fn_name.startswith("_") and not fn_name.startswith("__"),
        )
        self.functions[fn_name] = fn_model

    def visit_Assign(self, node: ast.Assign) -> None:
        if self._current_class is None:
            for target in node.targets:
                name = self._extract_name(target)
                if name and not name.startswith("__") and name not in _PYTHON_BUILTINS_AND_KEYWORDS:
                    self.states[name] = StateModel(
                        name=name,
                        namespace=self.module_name,
                        location=self._get_loc(node),
                        kind="atom",
                    )
        self.generic_visit(node)

    def _analyze_body(
        self, func_node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        """Extract called function names and Def-Use reads/writes/modifies variables."""
        calls: list[str] = []
        reads: list[str] = []
        writes: list[str] = []
        modifies: list[str] = []

        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                self._process_call_node(node, calls, modifies)
            elif isinstance(node, ast.Assign):
                self._process_assign_node(node, writes)
            elif isinstance(node, ast.AugAssign):
                self._process_aug_assign_node(node, modifies)
            elif isinstance(node, (ast.Name, ast.Attribute)) and isinstance(node.ctx, ast.Load):
                self._process_load_node(node, reads)

        return calls, reads, writes, modifies

    def _process_call_node(self, node: ast.Call, calls: list[str], modifies: list[str]) -> None:
        c_name = self._extract_name(node.func)
        if c_name and c_name not in _PYTHON_BUILTINS_AND_KEYWORDS:
            calls.append(c_name)
            if "." in c_name:
                obj, method = c_name.rsplit(".", 1)
                mutating = ("append", "extend", "insert", "pop", "remove", "update", "clear", "add", "discard")
                if method in mutating and obj and obj not in _PYTHON_BUILTINS_AND_KEYWORDS:
                    modifies.append(obj)

    def _process_assign_node(self, node: ast.Assign, writes: list[str]) -> None:
        for target in node.targets:
            t_name = self._extract_name(target)
            if t_name and len(t_name) > 1 and t_name not in _PYTHON_BUILTINS_AND_KEYWORDS:
                writes.append(t_name)

    def _process_aug_assign_node(self, node: ast.AugAssign, modifies: list[str]) -> None:
        t_name = self._extract_name(node.target)
        if t_name and len(t_name) > 1 and t_name not in _PYTHON_BUILTINS_AND_KEYWORDS:
            modifies.append(t_name)

    def _process_load_node(self, node: ast.Name | ast.Attribute, reads: list[str]) -> None:
        if isinstance(node, ast.Name):
            if node.id and len(node.id) > 1 and node.id not in _PYTHON_BUILTINS_AND_KEYWORDS:
                reads.append(node.id)
        elif isinstance(node, ast.Attribute):
            attr_full = self._extract_name(node)
            if attr_full and attr_full not in _PYTHON_BUILTINS_AND_KEYWORDS:
                reads.append(attr_full)


class PyParserAdapter(ParserPort):
    """Outbound port adapter implementing Python AST parsing for CodeModel generation."""

    def parse_source(self, source_code: str, file_path: str = "") -> NamespaceModel:
        """Parse single Python file into a domain NamespaceModel."""
        try:
            tree = ast.parse(source_code, filename=file_path or "<string>")
        except SyntaxError:
            # Fallback for files with syntax incompatibilities
            mod_name = os.path.splitext(os.path.basename(file_path))[0] if file_path else "global"
            return NamespaceModel(
                name=mod_name,
                file_path=file_path,
                docstring="",
                requires=[],
                imports=[],
                protocols={},
                records={},
                functions={},
                states={},
            )

        visitor = _PythonAstExtractor(file_path=file_path, source_code=source_code)
        visitor.visit(tree)

        doc = ast.get_docstring(tree) or ""
        return NamespaceModel(
            name=visitor.module_name,
            file_path=file_path,
            docstring=doc,
            requires=visitor.requires,
            imports=visitor.imports,
            protocols=visitor.protocols,
            records=visitor.records,
            functions=visitor.functions,
            states=visitor.states,
        )

    def parse_sources(self, sources: dict[str, str], max_workers: int | None = None) -> CodeModel:
        """Parse multiple Python files into a unified domain CodeModel."""
        model = CodeModel()
        if not sources:
            return model

        if len(sources) > 3:
            workers = max_workers or min(16, (os.cpu_count() or 4) * 2)
            with ThreadPoolExecutor(max_workers=workers) as executor:
                namespaces = list(
                    executor.map(
                        lambda item: self.parse_source(item[1], file_path=item[0]),
                        sources.items(),
                    )
                )
            for ns in namespaces:
                model.add_namespace(ns)
        else:
            for path, code in sources.items():
                ns = self.parse_source(code, file_path=path)
                model.add_namespace(ns)

        return model
