"""Tests for Python AST Parser Adapter."""

from pattern_detector.adapters.outbound.python_ast.py_parser_adapter import PyParserAdapter


def test_parse_namespace_and_classes() -> None:
    code = """
import os
import sys
from typing import Optional

class UserService:
    _instance: Optional["UserService"] = None

    def __init__(self, db_url: str = "") -> None:
        self.db_url = db_url

    @classmethod
    def get_instance(cls) -> "UserService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def process_user(self, user_id: str) -> None:
        print(f"Processing: {user_id}")
"""
    adapter = PyParserAdapter()
    ns = adapter.parse_source(code, file_path="user_service.py")

    assert ns.name == "user_service"
    assert "os" in ns.imports
    assert "sys" in ns.imports
    assert "UserService" in ns.records
    rec = ns.records["UserService"]
    assert rec.name == "UserService"
    assert "UserService._instance" in ns.states
    assert ns.states["UserService._instance"].is_once is True
    assert "db_url" in rec.fields


def test_parse_interfaces_and_implementations() -> None:
    code = """
from abc import ABC, abstractmethod

class ICrudRepository(ABC):
    @abstractmethod
    def save(self, entity: str) -> None:
        pass

    @abstractmethod
    def find_by_id(self, entity_id: str) -> str:
        pass

class DatabaseRepository(ICrudRepository):
    def save(self, entity: str) -> None:
        print(f"Saving: {entity}")

    def find_by_id(self, entity_id: str) -> str:
        return f"Entity {entity_id}"
"""
    adapter = PyParserAdapter()
    ns = adapter.parse_source(code, file_path="repo.py")

    assert "ICrudRepository" in ns.protocols
    proto = ns.protocols["ICrudRepository"]
    assert len(proto.methods) == 2
    assert "save" in [m.name for m in proto.methods]
    assert "find_by_id" in [m.name for m in proto.methods]

    assert "DatabaseRepository" in ns.records
    db_rec = ns.records["DatabaseRepository"]
    assert "ICrudRepository" in db_rec.implemented_protocols
