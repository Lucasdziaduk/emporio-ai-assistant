from datetime import date

import pytest

from app.domain.errors import NotFoundError
from app.domain.models import Category, Product
from app.domain.schemas import SearchProductsInput
from app.services.catalog_service import CatalogService


class FakeProductRepository:
    def __init__(self, products):
        self.products = products

    def list_all(self, *, limit=1000):
        return self.products[:limit]

    def get_by_id(self, product_id):
        return next((item for item in self.products if item.product_id == product_id), None)


class FakeCategoryRepository:
    def __init__(self, categories):
        self.categories = categories

    def list_all(self):
        return self.categories

    def get_by_id(self, category_id):
        return next((item for item in self.categories if item.category_id == category_id), None)


@pytest.fixture
def catalog_service():
    categories = [
        Category(category_id=1, name="Violões", description="Violões acústicos"),
        Category(category_id=2, name="Baixos", description="Baixos"),
    ]
    products = [
        Product(product_id=1, name="Yamaha C40 Nylon", price_cents=59990, category_id=1,
                description="Violão clássico de nylon", stock_quantity=12, status="active",
                specs={"strings": "nylon"}, created_at=date(2021, 3, 15)),
        Product(product_id=2, name="Giannini GF-3D", price_cents=79990, category_id=1,
                description="Violão acústico", stock_quantity=0, status="active",
                created_at=date(2020, 2, 28)),
        Product(product_id=3, name="Ibanez Bass", price_cents=44100, category_id=2,
                description="Baixo elétrico", stock_quantity=13, status="discontinued",
                created_at=date(2021, 8, 7)),
        Product(product_id=4, name="Violão Natural", price_cents=89900, category_id=1,
                description="Violão de aço", stock_quantity=5, status="active",
                created_at=date(2022, 5, 10)),
    ]
    return CatalogService(FakeProductRepository(products), FakeCategoryRepository(categories))


def test_search_filters_category_price_and_availability(catalog_service):
    result = catalog_service.search_products(SearchProductsInput(
        category="Violões", max_price_brl=1000, availability="available"
    ))
    assert result.total_matches == 2
    assert result.returned == 2
    assert all(item.availability.value == "available" for item in result.products)


def test_search_is_case_and_accent_insensitive(catalog_service):
    result = catalog_service.search_products(SearchProductsInput(query="VIOLAO NYLON", category="violoes"))
    assert result.total_matches == 1
    assert result.products[0].name == "Yamaha C40 Nylon"


def test_search_can_include_unavailable_products(catalog_service):
    result = catalog_service.search_products(SearchProductsInput(availability="all"))
    assert result.total_matches == 4


def test_search_limit_and_truncation(catalog_service):
    result = catalog_service.search_products(SearchProductsInput(category="Violões", availability="all", limit=2))
    assert result.total_matches == 3
    assert result.returned == 2
    assert result.truncated is True


def test_search_sorts_descending(catalog_service):
    result = catalog_service.search_products(SearchProductsInput(availability="all", sort_by="price_desc"))
    prices = [item.price_cents for item in result.products]
    assert prices == sorted(prices, reverse=True)


def test_search_returns_empty_list_without_fabricating_matches(catalog_service):
    result = catalog_service.search_products(SearchProductsInput(query="instrumento inexistente"))
    assert result.total_matches == 0
    assert result.products == []


def test_get_product_by_id(catalog_service):
    assert catalog_service.get_product_by_id(1).name == "Yamaha C40 Nylon"


def test_get_product_missing_raises(catalog_service):
    with pytest.raises(NotFoundError):
        catalog_service.get_product_by_id(999)


def test_get_product_details_maps_category_and_formats_price(catalog_service):
    details = catalog_service.get_product_details(1)
    assert details.category == "Violões"
    assert details.formatted_price == "R$ 599,90"
    assert details.specs["strings"] == "nylon"
