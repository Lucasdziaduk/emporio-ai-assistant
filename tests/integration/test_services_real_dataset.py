"""Integration checks against local challenge data (skipped without private files)."""

from pathlib import Path

import pytest

from app.data import (
    CategoryRepository,
    CustomerRepository,
    DatasetRepository,
    OrderRepository,
    ProductRepository,
    PromotionRepository,
    create_connection,
    load_dataset,
)
from app.services import (
    CatalogService,
    IdentityService,
    OrderService,
    PaymentService,
    PolicyService,
    PromotionService,
    StoreInformationService,
)
from app.domain.schemas import GetPurchaseConditionsInput, SearchProductsInput


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "private" / "source"
POLICY_PDF = ROOT / "data" / "private" / "store_policies.pdf"
REQUIRED = ["products.csv", "categories.csv", "promotions.csv", "customers.csv", "orders.csv", "order_items.csv"]

pytestmark = pytest.mark.skipif(
    not SOURCE.is_dir() or not all((SOURCE / name).is_file() for name in REQUIRED),
    reason="Original challenge CSVs are not present in data/private/source.",
)


@pytest.fixture
def services():
    connection = create_connection(":memory:")
    load_dataset(SOURCE, connection)
    products = ProductRepository(connection)
    categories = CategoryRepository(connection)
    promotions = PromotionRepository(connection)
    customers = CustomerRepository(connection)
    orders = OrderRepository(connection)
    dataset = DatasetRepository(connection)
    promotion_service = PromotionService(promotions, products)
    catalog_service = CatalogService(products, categories, promotion_service)
    payment_service = PaymentService(products, promotion_service)
    identity_service = IdentityService(customers, orders)
    order_service = OrderService(orders, products, dataset)
    yield connection, catalog_service, promotion_service, payment_service, identity_service, order_service
    connection.close()


def test_real_dataset_product_search_returns_expected_12(services):
    _, catalog, *_ = services
    result = catalog.search_products(SearchProductsInput(
        category="Violões", max_price_brl=1000, availability="available", limit=10
    ))
    assert result.total_matches == 12
    assert result.returned == 10
    assert result.truncated is True


def test_real_takamine_pix_price_is_correct(services):
    _, _, _, payment, *_ = services
    result = payment.get_purchase_conditions(GetPurchaseConditionsInput(
        product_id=95, payment_method="pix"
    ))
    assert result.list_price_cents == 219900
    assert result.final_price_cents == 208905


def test_real_active_promotions_are_not_combined_with_pix(services):
    _, _, promotions, payment, *_ = services
    summary = promotions.get_promotion_summary(127)
    assert summary is not None
    assert summary.promotional_price_cents == 32310
    result = payment.get_purchase_conditions(GetPurchaseConditionsInput(
        product_id=127, payment_method="pix"
    ))
    assert result.final_price_cents == 32310
    assert result.discount_percent == 10


def test_real_order_identity_and_authorized_status(services):
    _, _, _, _, identity, order_service = services
    grant = identity.verify_order_access(
        1, "(67) 98432-1098", session_id="integration-session"
    )
    result = order_service.get_order_status(
        1, authorization=grant, session_id="integration-session"
    )
    assert result.order_id == 1
    assert result.dataset_is_static is True
    assert result.latest_order_date_in_dataset.isoformat() == "2026-03-22"


def test_real_policy_pdf_can_be_extracted_and_searched():
    if not POLICY_PDF.is_file():
        pytest.skip("Policy PDF is not present in data/private.")
    service = PolicyService(POLICY_PDF)
    chunks = service.extract_policy_chunks(POLICY_PDF)
    sections = {chunk.section for chunk in chunks}
    assert {"1", "1.1", "1.2", "2", "3", "3.1", "4.1", "5.1", "5.2", "5.3", "6.1", "6.2", "7.1", "7.2", "7.3", "8.1", "8.2", "8.3", "9", "10"}.issubset(sections)
    assert "5" not in sections  # shipping transit ranges are not section headings
    result = service.search("Qual o prazo de arrependimento para compra online?")
    assert result.results
    assert result.results[0].section == "4.1"


def test_store_information_is_available_without_llm():
    result = StoreInformationService().get_information("opening_hours")
    assert result.content["monday_to_friday"] == "09:00 às 18:00"


def test_real_product_details_include_active_promotion(services):
    _, catalog, *_ = services
    details = catalog.get_product_details(127)
    assert details.name == "Kalani KAL-700T Tenor Natural"
    assert details.promotion is not None
    assert details.promotion.promotional_price_cents == 32310
