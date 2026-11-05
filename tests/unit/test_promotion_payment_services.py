from datetime import date

import pytest

from app.domain.errors import InvalidInputError, PolicyConflictError
from app.services.exceptions import InstallmentNotAllowedError, ProductUnavailableError
from app.domain.models import Product, Promotion
from app.domain.schemas import GetPurchaseConditionsInput
from app.services.payment_service import PaymentService
from app.services.promotion_service import PromotionService


class FakeProductRepository:
    def __init__(self, products):
        self.products = {item.product_id: item for item in products}

    def get_by_id(self, product_id):
        return self.products.get(product_id)


class FakePromotionRepository:
    def __init__(self, promotions):
        self.promotions = promotions

    def list_active_for_product(self, product_id):
        return [p for p in self.promotions if p.product_id == product_id and p.is_active]


def build_services():
    products = [
        Product(product_id=1, name="Promo Guitar", price_cents=100000, category_id=1,
                description="Instrument", stock_quantity=5, status="active", created_at=date(2024, 1, 1)),
        Product(product_id=2, name="Regular Guitar", price_cents=200000, category_id=1,
                description="Instrument", stock_quantity=3, status="active", created_at=date(2024, 1, 1)),
        Product(product_id=3, name="Sold Out Guitar", price_cents=50000, category_id=1,
                description="Instrument", stock_quantity=0, status="active", created_at=date(2024, 1, 1)),
        Product(product_id=4, name="Conflicted Guitar", price_cents=100000, category_id=1,
                description="Instrument", stock_quantity=1, status="active", created_at=date(2024, 1, 1)),
    ]
    promotions = [
        Promotion(promotion_id=1, product_id=1, discount_percent=10, description="Offer", is_active=True),
        Promotion(promotion_id=2, product_id=4, discount_percent=10, description="Offer A", is_active=True),
        Promotion(promotion_id=3, product_id=4, discount_percent=15, description="Offer B", is_active=True),
    ]
    product_repo = FakeProductRepository(products)
    promotion_repo = FakePromotionRepository(promotions)
    promotion_service = PromotionService(promotion_repo, product_repo)
    payment_service = PaymentService(product_repo, promotion_service)
    return product_repo, promotion_repo, promotion_service, payment_service


def test_promotional_price_calculation():
    assert PromotionService.calculate_promotional_price(35900, 10) == 32310
    assert PromotionService.calculate_promotional_price(54900, 20) == 43920


def test_promotion_summary_is_returned_for_available_product():
    _, _, service, _ = build_services()
    summary = service.get_promotion_summary(1)
    assert summary is not None
    assert summary.promotional_price_cents == 90000


def test_multiple_active_promotions_raise_conflict():
    _, _, service, _ = build_services()
    with pytest.raises(PolicyConflictError):
        service.get_active_promotion(4)


def test_pix_discount_applies_when_no_promotion_exists():
    _, _, _, service = build_services()
    result = service.get_purchase_conditions(GetPurchaseConditionsInput(product_id=2, payment_method="pix"))
    assert result.discount_percent == 5
    assert result.discount_cents == 10000
    assert result.final_price_cents == 190000


def test_pix_discount_does_not_accumulate_with_promotion():
    _, _, _, service = build_services()
    result = service.get_purchase_conditions(GetPurchaseConditionsInput(product_id=1, payment_method="pix"))
    assert result.discount_percent == 10
    assert result.discount_cents == 10000
    assert result.final_price_cents == 90000


def test_credit_installment_split_preserves_exact_total():
    _, _, _, service = build_services()
    result = service.get_purchase_conditions(GetPurchaseConditionsInput(
        product_id=2, payment_method="credit", installments=3
    ))
    assert result.installment_amounts_cents == [66667, 66667, 66666]
    assert sum(result.installment_amounts_cents) == result.final_price_cents


def test_detailed_minimum_installment_rule_is_applied():
    _, _, _, service = build_services()
    with pytest.raises(InstallmentNotAllowedError):
        service.get_purchase_conditions(GetPurchaseConditionsInput(
            product_id=1, payment_method="credit", installments=12
        ))


def test_unavailable_product_cannot_be_priced_as_purchaseable():
    _, _, _, service = build_services()
    with pytest.raises(ProductUnavailableError):
        service.get_purchase_conditions(GetPurchaseConditionsInput(product_id=3, payment_method="pix"))


def test_minimum_installment_schedule():
    assert PaymentService.minimum_installment_cents(2) == 5000
    assert PaymentService.minimum_installment_cents(5) == 8000
    assert PaymentService.minimum_installment_cents(10) == 10000
