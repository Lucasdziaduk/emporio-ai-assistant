"""Promotion lookup and deterministic promotional-price calculation."""

from decimal import Decimal, ROUND_HALF_UP

from app.data.repositories import ProductRepository, PromotionRepository
from app.domain.errors import NotFoundError, PolicyConflictError
from app.domain.models import Product, Promotion
from app.domain.enums import ProductAvailability
from app.domain.schemas import PromotionSummary
from app.services.money import cents_to_brl


class PromotionService:
    """Resolve active promotions without selecting conflicts arbitrarily."""

    def __init__(
        self,
        promotion_repository: PromotionRepository,
        product_repository: ProductRepository,
    ) -> None:
        self.promotion_repository = promotion_repository
        self.product_repository = product_repository

    def get_active_promotion(self, product_id: int) -> Promotion | None:
        """Return the sole active promotion, None, or raise on ambiguity."""
        product = self.product_repository.get_by_id(product_id)
        if product is None:
            raise NotFoundError()
        promotions = self.promotion_repository.list_active_for_product(product_id)
        if len(promotions) > 1:
            raise PolicyConflictError()
        return promotions[0] if promotions else None

    @staticmethod
    def calculate_promotional_price(
        original_price_cents: int,
        discount_percent: int,
    ) -> int:
        """Calculate a percentage discount using half-up cent rounding."""
        if original_price_cents < 0 or not 1 <= discount_percent <= 100:
            raise ValueError("Invalid price or discount percentage.")
        multiplier = Decimal(100 - discount_percent) / Decimal(100)
        result = (Decimal(original_price_cents) * multiplier).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        return int(result)

    def get_promotion_summary(self, product_id: int) -> PromotionSummary | None:
        """Return a presentation-safe active promotion for an available product."""
        product: Product | None = self.product_repository.get_by_id(product_id)
        if product is None:
            raise NotFoundError()
        promotion = self.get_active_promotion(product_id)
        if promotion is None or product.availability != ProductAvailability.AVAILABLE:
            return None
        promo_price = self.calculate_promotional_price(
            product.price_cents, promotion.discount_percent
        )
        return PromotionSummary(
            promotion_id=promotion.promotion_id,
            description=promotion.description,
            discount_percent=promotion.discount_percent,
            original_price_cents=product.price_cents,
            promotional_price_cents=promo_price,
            formatted_promotional_price=cents_to_brl(promo_price),
        )
