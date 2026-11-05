"""Deterministic payment, PIX discount and installment calculations."""

from decimal import Decimal, ROUND_HALF_UP

from app.data.repositories import ProductRepository
from app.domain.enums import ProductAvailability
from app.domain.errors import NotFoundError, InvalidInputError
from app.services.exceptions import ProductUnavailableError, InstallmentNotAllowedError
from app.domain.schemas import GetPurchaseConditionsInput, PurchaseConditionsData
from app.services.money import cents_to_brl
from app.services.promotion_service import PromotionService


class PaymentService:
    """Calculate payment conditions strictly from catalog and policy rules."""

    PIX_DISCOUNT_PERCENT = 5

    # Detailed rules in policy manual section 3.1.
    INSTALLMENT_MINIMUM_CENTS = (
        (1, 3, 5_000),
        (4, 6, 8_000),
        (7, 12, 10_000),
    )

    def __init__(
        self,
        product_repository: ProductRepository,
        promotion_service: PromotionService,
    ) -> None:
        self.product_repository = product_repository
        self.promotion_service = promotion_service

    @classmethod
    def minimum_installment_cents(cls, installments: int) -> int:
        if not 1 <= installments <= 12:
            raise InvalidInputError()
        for lower, upper, minimum in cls.INSTALLMENT_MINIMUM_CENTS:
            if lower <= installments <= upper:
                return minimum
        raise InvalidInputError()

    @staticmethod
    def split_into_installments(total_cents: int, count: int) -> list[int]:
        """Split cents exactly; distribute remainder cents to first installments."""
        if total_cents < 0 or count < 1:
            raise ValueError("Invalid total or installment count.")
        base, remainder = divmod(total_cents, count)
        return [base + (1 if index < remainder else 0) for index in range(count)]

    @staticmethod
    def _percent_amount(amount_cents: int, percent: int) -> int:
        value = (Decimal(amount_cents) * Decimal(percent) / Decimal(100)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        return int(value)

    def get_purchase_conditions(
        self,
        request: GetPurchaseConditionsInput,
    ) -> PurchaseConditionsData:
        product = self.product_repository.get_by_id(request.product_id)
        if product is None:
            raise NotFoundError()
        if product.availability != ProductAvailability.AVAILABLE:
            raise ProductUnavailableError()

        promotion = self.promotion_service.get_promotion_summary(product.product_id)
        list_price = product.price_cents

        if promotion is not None:
            final_price = promotion.promotional_price_cents
            discount_percent = promotion.discount_percent
        elif request.payment_method == "pix":
            discount = self._percent_amount(list_price, self.PIX_DISCOUNT_PERCENT)
            final_price = list_price - discount
            discount_percent = self.PIX_DISCOUNT_PERCENT
        else:
            final_price = list_price
            discount_percent = 0

        discount_cents = list_price - final_price
        installment_amounts: list[int] = []

        if request.payment_method == "credit" and request.installments is not None:
            count = request.installments
            minimum = self.minimum_installment_cents(count)
            installment_amounts = self.split_into_installments(final_price, count)
            if any(amount < minimum for amount in installment_amounts):
                raise InstallmentNotAllowedError()

        return PurchaseConditionsData(
            product_id=product.product_id,
            list_price_cents=list_price,
            promotion=promotion,
            payment_method=request.payment_method,
            discount_percent=discount_percent,
            discount_cents=discount_cents,
            final_price_cents=final_price,
            formatted_final_price=cents_to_brl(final_price),
            installments=request.installments,
            installment_amounts_cents=installment_amounts,
        )
