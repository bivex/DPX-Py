"""Showcase of Clean Code, SOLID Principles and Anti-Pattern Detection in Python."""

from __future__ import annotations

from abc import ABC, abstractmethod


# 1. SRP: God Class Anti-Pattern
class GodApplicationManager:
    """God Object combining unrelated responsibilities."""

    def save_user_to_database(self) -> None:
        pass

    def delete_user_from_database(self) -> None:
        pass

    def query_user_records(self) -> None:
        pass

    def send_http_webhook(self) -> None:
        pass

    def parse_http_payload(self) -> None:
        pass

    def render_html_template(self) -> None:
        pass

    def generate_pdf_report(self) -> None:
        pass

    def calculate_corporate_tax(self) -> None:
        pass

    def validate_credit_card(self) -> None:
        pass

    def send_smtp_email(self) -> None:
        pass

    def resize_user_avatar(self) -> None:
        pass

    def encrypt_master_keys(self) -> None:
        pass


# 2. OCP: Type-Inspection Cascade Violation
class PaymentProcessor:
    def process_payment(self, payment_method: object) -> None:
        if isinstance(payment_method, str) and payment_method == "CARD":
            print("Processing Card")
        elif isinstance(payment_method, str) and payment_method == "PAYPAL":
            print("Processing PayPal")
        elif isinstance(payment_method, str) and payment_method == "CRYPTO":
            print("Processing Crypto")


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


# 5. Law of Demeter: Train Wreck Violation
class OrderReportService:
    def get_order_postcode(self, order: object) -> str:
        # Train wreck method chaining violating Law of Demeter
        return order.get_customer().get_profile().get_address().get_postal_code()
