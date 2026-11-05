"""Composition root for wiring repositories and business services."""

from dataclasses import dataclass
import sqlite3
from pathlib import Path

from app.data.repositories import (
    CategoryRepository,
    CustomerRepository,
    DatasetRepository,
    OrderRepository,
    ProductRepository,
    PromotionRepository,
)
from app.services.catalog_service import CatalogService
from app.services.identity_service import IdentityService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.policy_service import PolicyService
from app.services.promotion_service import PromotionService
from app.services.store_service import StoreInformationService


@dataclass(frozen=True)
class ServiceContainer:
    """Ready-to-use business services sharing one SQLite connection."""

    catalog: CatalogService
    promotions: PromotionService
    payments: PaymentService
    orders: OrderService
    identity: IdentityService
    policies: PolicyService
    store_information: StoreInformationService


def build_service_container(
    connection: sqlite3.Connection,
    *,
    policy_pdf_path: str | Path | None = None,
    auth_ttl_minutes: int = 10,
    max_auth_attempts: int = 3,
) -> ServiceContainer:
    """Wire repositories and independent business services.

    The SQLite connection must already contain a successfully loaded dataset.
    Policy PDF extraction is lazy and happens on the first policy search.
    """
    products = ProductRepository(connection)
    categories = CategoryRepository(connection)
    promotions = PromotionRepository(connection)
    customers = CustomerRepository(connection)
    orders = OrderRepository(connection)
    dataset = DatasetRepository(connection)

    promotion_service = PromotionService(promotions, products)
    return ServiceContainer(
        catalog=CatalogService(products, categories, promotion_service),
        promotions=promotion_service,
        payments=PaymentService(products, promotion_service),
        orders=OrderService(orders, products, dataset),
        identity=IdentityService(
            customers,
            orders,
            auth_ttl_minutes=auth_ttl_minutes,
            max_attempts=max_auth_attempts,
        ),
        policies=PolicyService(policy_pdf_path),
        store_information=StoreInformationService(),
    )
