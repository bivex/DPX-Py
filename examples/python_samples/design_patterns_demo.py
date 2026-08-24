"""Showcase of GoF Design Patterns implemented idiomatically in Python."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


# 1. Creational: Singleton
class DatabaseConnection:
    """Thread-safe Singleton holding global database connection state."""

    _instance: DatabaseConnection | None = None

    @classmethod
    def get_instance(cls) -> DatabaseConnection:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def query(self, sql: str) -> str:
        return f"Executing {sql}"


# 2. Creational: Builder Pattern
class HttpRequestBuilder:
    """Fluent Builder for constructing immutable HTTP requests."""

    def __init__(self) -> None:
        self._url: str = ""
        self._method: str = "GET"
        self._headers: dict[str, str] = {}
        self._body: str = ""

    def url(self, url: str) -> HttpRequestBuilder:
        self._url = url
        return self

    def method(self, method: str) -> HttpRequestBuilder:
        self._method = method
        return self

    def header(self, key: str, value: str) -> HttpRequestBuilder:
        self._headers[key] = value
        return self

    def body(self, body: str) -> HttpRequestBuilder:
        self._body = body
        return self

    def build(self) -> dict[str, Any]:
        return {
            "url": self._url,
            "method": self._method,
            "headers": self._headers,
            "body": self._body,
        }


# 3. Behavioral: Strategy Pattern
class PaymentStrategy(ABC):
    @abstractmethod
    def pay(self, amount: float) -> bool:
        pass


class CreditCardPayment(PaymentStrategy):
    def pay(self, amount: float) -> bool:
        print(f"Paying ${amount} via Credit Card")
        return True


class CryptoPayment(PaymentStrategy):
    def pay(self, amount: float) -> bool:
        print(f"Paying ${amount} via Bitcoin")
        return True


class OrderCheckout:
    def __init__(self, payment_strategy: PaymentStrategy) -> None:
        self.payment_strategy = payment_strategy

    def complete_order(self, amount: float) -> bool:
        return self.payment_strategy.pay(amount)


# 4. Behavioral: Observer / Reactive Pattern
class ObservableState:
    """Reactive state container notifying subscribers on mutation."""

    def __init__(self, initial_value: str) -> None:
        self._value: str = initial_value
        self._listeners: list[Callable[[str], None]] = []

    def get(self) -> str:
        return self._value

    def set(self, new_value: str) -> None:
        if self._value != new_value:
            self._value = new_value
            self.notify(new_value)

    def subscribe(self, listener: Callable[[str], None]) -> None:
        self._listeners.append(listener)

    def notify(self, value: str) -> None:
        for listener in self._listeners:
            listener(value)


# 5. Structural: Composite Pattern
class FileSystemNode(ABC):
    @abstractmethod
    def get_size(self) -> int:
        pass


class FileLeaf(FileSystemNode):
    def __init__(self, name: str, size: int) -> None:
        self.name = name
        self.size = size

    def get_size(self) -> int:
        return self.size


class DirectoryComposite(FileSystemNode):
    def __init__(self, name: str) -> None:
        self.name = name
        self.children: list[FileSystemNode] = []

    def add(self, node: FileSystemNode) -> None:
        self.children.append(node)

    def get_size(self) -> int:
        total = 0
        for child in self.children:
            total += child.get_size()
        return total
