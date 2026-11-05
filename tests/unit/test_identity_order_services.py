from datetime import date, datetime, timedelta, timezone

import pytest

from app.domain.errors import AuthenticationFailedError, AuthenticationRequiredError
from app.domain.models import Order, OrderItem, Product
from app.services.identity_service import IdentityService
from app.services.order_service import OrderService


class FakeCustomerRepository:
    def __init__(self, customers):
        self.customers = {customer.customer_id: customer for customer in customers}

    def get_by_id(self, customer_id):
        return self.customers.get(customer_id)


class FakeOrderRepository:
    def __init__(self, orders, items=None):
        self.orders = {order.order_id: order for order in orders}
        self.items = items or {}

    def get_customer_id(self, order_id):
        order = self.orders.get(order_id)
        return order.customer_id if order else None

    def get_by_id(self, order_id):
        return self.orders.get(order_id)

    def get_items(self, order_id):
        return self.items.get(order_id, [])


class FakeProductRepository:
    def __init__(self, products):
        self.products = {product.product_id: product for product in products}

    def get_by_id(self, product_id):
        return self.products.get(product_id)


class FakeDatasetRepository:
    def get_metadata(self):
        return {"latest_order_date": "2026-03-22"}


def setup_services():
    from app.domain.models import Customer

    customer = Customer(
        customer_id=7, name="Cliente Teste", phone="(67) 99999-1111",
        email="test@example.com", city="Campo Grande"
    )
    order = Order(
        order_id=42, customer_id=7, order_date=date(2026, 2, 1), status="shipped",
        total_cents=120000, payment_method="pix", tracking_code="BR123456789BR",
        estimated_delivery=date(2026, 2, 8), notes=None
    )
    product = Product(
        product_id=81, name="Yamaha C40", price_cents=59990, category_id=5,
        description="Violão", stock_quantity=3, status="active", created_at=date(2021, 1, 1)
    )
    customers = FakeCustomerRepository([customer])
    orders = FakeOrderRepository([order], {42: [OrderItem(order_id=42, product_id=81, quantity=2)]})
    products = FakeProductRepository([product])
    identity = IdentityService(customers, orders, auth_ttl_minutes=10, max_attempts=3)
    order_service = OrderService(orders, products, FakeDatasetRepository())
    return identity, order_service


def test_identity_verification_grants_session_scoped_access():
    identity, order_service = setup_services()
    now = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
    grant = identity.verify_order_access(
        42, "(67) 99999-1111", session_id="session-a", now=now
    )
    result = order_service.get_order_status(
        42, authorization=grant, session_id="session-a", now=now + timedelta(minutes=1)
    )
    assert result.order_id == 42
    assert result.items[0].product_name == "Yamaha C40"
    assert result.dataset_is_static is True
    assert result.latest_order_date_in_dataset == date(2026, 3, 22)


def test_wrong_phone_does_not_grant_access():
    identity, _ = setup_services()
    with pytest.raises(AuthenticationFailedError):
        identity.verify_order_access(42, "(67) 98888-2222", session_id="session-a")
    assert identity.attempts_remaining("session-a") == 2


def test_third_failure_locks_session_verification():
    identity, _ = setup_services()
    for _ in range(3):
        with pytest.raises(AuthenticationFailedError):
            identity.verify_order_access(42, "(67) 98888-2222", session_id="session-a")
    assert identity.attempts_remaining("session-a") == 0
    with pytest.raises(AuthenticationFailedError):
        identity.verify_order_access(42, "(67) 99999-1111", session_id="session-a")


def test_nonexistent_order_and_wrong_phone_use_same_public_error():
    identity, _ = setup_services()
    with pytest.raises(AuthenticationFailedError):
        identity.verify_order_access(999, "(67) 99999-1111", session_id="session-a")


def test_order_grant_cannot_be_reused_in_another_session():
    identity, order_service = setup_services()
    grant = identity.verify_order_access(42, "(67) 99999-1111", session_id="session-a")
    with pytest.raises(AuthenticationRequiredError):
        order_service.get_order_status(42, authorization=grant, session_id="session-b")


def test_expired_order_grant_is_rejected():
    identity, order_service = setup_services()
    now = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
    grant = identity.verify_order_access(42, "(67) 99999-1111", session_id="session-a", now=now)
    with pytest.raises(AuthenticationRequiredError):
        order_service.get_order_status(
            42, authorization=grant, session_id="session-a", now=now + timedelta(minutes=11)
        )


def test_order_lookup_without_grant_is_rejected():
    _, order_service = setup_services()
    with pytest.raises(AuthenticationRequiredError):
        order_service.get_order_status(42, authorization=None, session_id="session-a")
