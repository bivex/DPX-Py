"""Showcase of Clean Code, SOLID Principles and Design Patterns in Python."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


# 1. SRP: Cohesive Single Responsibility Services
class UserPersistenceService:
    """Manages user persistence operations."""

    def save_user(self, user_id: str) -> None:
        pass

    def delete_user(self, user_id: str) -> None:
        pass

    def query_users(self) -> list[str]:
        return []


class NotificationService:
    """Manages external user notifications."""

    def send_webhook(self, url: str, payload: dict[str, Any]) -> None:
        pass

    def send_email(self, recipient: str, subject: str) -> None:
        pass


class ReportGenerationService:
    """Generates document reports."""

    def render_html(self, template_name: str) -> str:
        return ""

    def generate_pdf(self, report_id: str) -> bytes:
        return b""


# 2. OCP: Polymorphic Open Extension
class IPaymentMethodHandler(ABC):
    """Abstract Strategy enabling open extension without modifying processor."""

    @abstractmethod
    def execute_payment(self, amount: float) -> None:
        pass


class CardPaymentMethodHandler(IPaymentMethodHandler):
    def execute_payment(self, amount: float) -> None:
        print(f"Processing Card payment: ${amount:.2f}")


class PayPalPaymentMethodHandler(IPaymentMethodHandler):
    def execute_payment(self, amount: float) -> None:
        print(f"Processing PayPal payment: ${amount:.2f}")


class CryptoPaymentMethodHandler(IPaymentMethodHandler):
    def execute_payment(self, amount: float) -> None:
        print(f"Processing Crypto payment: ${amount:.2f}")


class PaymentProcessor:
    """Adheres to OCP by delegating execution to polymorphic IPaymentMethodHandler strategies."""

    def __init__(self, handlers: dict[str, IPaymentMethodHandler] | None = None) -> None:
        self._handlers: dict[str, IPaymentMethodHandler] = handlers or {
            "CARD": CardPaymentMethodHandler(),
            "PAYPAL": PayPalPaymentMethodHandler(),
            "CRYPTO": CryptoPaymentMethodHandler(),
        }

    def process_payment(self, payment_type: str, amount: float) -> None:
        handler = self._handlers.get(payment_type)
        if handler:
            handler.execute_payment(amount)


# 3. LSP: Subclass Contract Adherence
class BaseRepository(ABC):
    @abstractmethod
    def read_all(self) -> list[str]:
        pass


class WritableRepository(BaseRepository):
    @abstractmethod
    def write_one(self, item: str) -> None:
        pass


class ImmutableRepository(BaseRepository):
    def read_all(self) -> list[str]:
        return ["item1", "item2"]


# 4. ISP: Segregated Role Interfaces
class IBackendDeveloper(ABC):
    @abstractmethod
    def develop_backend(self) -> None:
        pass

    @abstractmethod
    def optimize_sql_queries(self) -> None:
        pass


class IDesigner(ABC):
    @abstractmethod
    def design_figma_mockups(self) -> None:
        pass


class IDevOps(ABC):
    @abstractmethod
    def setup_kubernetes_clusters(self) -> None:
        pass


# 5. Law of Demeter: Encapsulated Tell-Don't-Ask Navigation
class OrderReportService:
    """Respects Law of Demeter by interacting only with immediate dependencies."""

    def get_order_postcode(self, order: Any) -> str:
        return order.get_delivery_postal_code()
