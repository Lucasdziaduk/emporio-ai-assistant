"""Business logic for product catalog search and details."""

from __future__ import annotations

import unicodedata

from app.data.repositories import CategoryRepository, ProductRepository
from app.domain.errors import NotFoundError
from app.domain.models import Product
from app.domain.schemas import (
    ProductDetailsData,
    ProductSearchData,
    ProductSummary,
    SearchProductsInput,
)
from app.services.money import cents_to_brl, reais_to_cents


def normalize_text(value: str) -> str:
    """Normalize text for case- and accent-insensitive matching."""
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(
        character for character in normalized
        if not unicodedata.combining(character)
    )


class CatalogService:
    """Search and retrieve catalog products using repositories."""

    def __init__(
        self,
        product_repository: ProductRepository,
        category_repository: CategoryRepository,
        promotion_service=None,
    ) -> None:
        self.product_repository = product_repository
        self.category_repository = category_repository
        self.promotion_service = promotion_service

    def search_products(self, filters: SearchProductsInput) -> ProductSearchData:
        """Apply text, category, price, availability, sort and limit filters."""
        products = self.product_repository.list_all(limit=5000)
        categories = self.category_repository.list_all()
        category_names = {item.category_id: item.name for item in categories}

        wanted_category = normalize_text(filters.category) if filters.category else None
        terms = normalize_text(filters.query).split() if filters.query else []
        minimum = reais_to_cents(filters.min_price_brl) if filters.min_price_brl is not None else None
        maximum = reais_to_cents(filters.max_price_brl) if filters.max_price_brl is not None else None

        matches: list[Product] = []
        for product in products:
            category_name = category_names.get(product.category_id, "")
            if wanted_category and normalize_text(category_name) != wanted_category:
                continue

            searchable = normalize_text(" ".join([
                product.name,
                product.description,
                category_name,
                *product.specs.keys(),
                *product.specs.values(),
            ]))
            if terms and not all(term in searchable for term in terms):
                continue
            if minimum is not None and product.price_cents < minimum:
                continue
            if maximum is not None and product.price_cents > maximum:
                continue
            if filters.availability != "all" and product.availability.value != filters.availability:
                continue
            matches.append(product)

        if filters.sort_by == "price_asc":
            matches.sort(key=lambda item: (item.price_cents, item.product_id))
        elif filters.sort_by == "price_desc":
            matches.sort(key=lambda item: (-item.price_cents, item.product_id))
        else:
            matches.sort(key=lambda item: (normalize_text(item.name), item.product_id))

        total = len(matches)
        selected = matches[:filters.limit]
        summaries = [
            ProductSummary(
                product_id=item.product_id,
                name=item.name,
                price_cents=item.price_cents,
                formatted_price=cents_to_brl(item.price_cents),
                stock_quantity=item.stock_quantity,
                availability=item.availability,
                category=category_names.get(item.category_id, "Categoria não identificada"),
            )
            for item in selected
        ]
        return ProductSearchData(
            total_matches=total,
            returned=len(summaries),
            truncated=total > len(summaries),
            products=summaries,
        )

    def get_product_by_id(self, product_id: int) -> Product:
        """Return a product or raise a safe not-found exception."""
        product = self.product_repository.get_by_id(product_id)
        if product is None:
            raise NotFoundError()
        return product

    def get_product_details(self, product_id: int) -> ProductDetailsData:
        """Build the detailed response schema for one product."""
        product = self.get_product_by_id(product_id)
        category = self.category_repository.get_by_id(product.category_id)
        promotion = None
        if self.promotion_service is not None:
            promotion = self.promotion_service.get_promotion_summary(product_id)
        return ProductDetailsData(
            product_id=product.product_id,
            name=product.name,
            category=category.name if category else "Categoria não identificada",
            status=product.status,
            availability=product.availability,
            price_cents=product.price_cents,
            formatted_price=cents_to_brl(product.price_cents),
            stock_quantity=product.stock_quantity,
            description=product.description,
            specs=product.specs,
            created_at=product.created_at,
            promotion=promotion,
        )
