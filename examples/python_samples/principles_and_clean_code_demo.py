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


# 3. LSP: Subclass Contract Breach
class ReadOnlyRepository(ABC):
    @abstractmethod
    def read_all(self) -> list[str]:
        pass

    @abstractmethod
    def write_one(self, item: str) -> None:
        pass


class ImmutableRepository(ReadOnlyRepository):
    def read_all(self) -> list[str]:
        return ["item1", "item2"]

    def write_one(self, item: str) -> None:
        raise NotImplementedError("Writing is prohibited in ImmutableRepository")


# 4. ISP: Fat Monolithic Interface
class IFatWorker(ABC):
    @abstractmethod
    def develop_backend(self) -> None:
        pass

    @abstractmethod
    def design_figma_mockups(self) -> None:
        pass

    @abstractmethod
    def setup_kubernetes_clusters(self) -> None:
        pass

    @abstractmethod
    def optimize_sql_queries(self) -> None:
        pass

    @abstractmethod
    def run_sales_demos(self) -> None:
        pass

    @abstractmethod
    def calculate_payroll(self) -> None:
        pass

    @abstractmethod
    def interview_candidates(self) -> None:
        pass

    @abstractmethod
    def clean_kitchen(self) -> None:
        pass


# 5. Law of Demeter: Train Wreck Violation
class OrderReportService:
    def get_order_postcode(self, order: object) -> str:
        # Train wreck method chaining violating Law of Demeter
        return order.get_customer().get_profile().get_address().get_postal_code()
