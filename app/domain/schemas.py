
"""Input and output schemas for application services and agent tools."""

from datetime import date
from decimal import Decimal
from typing import Any, Generic, Literal, TypeVar

from pydantic import Field, SecretStr, field_validator, model_validator

from app.domain.enums import OrderStatus, ProductAvailability, ProductStatus
from app.domain.models import DomainModel


# ============================================================
# COMMON TYPES
# ============================================================

ToolName = Literal[
    "search_products",
    "get_product_details",
    "get_order_status",
    "search_store_policies",
    "get_store_information",
    "get_purchase_conditions",
]

ToolErrorCode = Literal[
    "VALIDATION_ERROR",
    "NOT_FOUND",
    "AMBIGUOUS_RESULT",
    "AUTH_REQUIRED",
    "AUTH_FAILED",
    "POLICY_CONFLICT",
    "INSUFFICIENT_EVIDENCE",
    "SOURCE_UNAVAILABLE",
    "INTERNAL_ERROR",
]

SourceType = Literal[
    "products_csv",
    "promotions_csv",
    "orders_csv",
    "policy_manual",
    "store_information",
]


# ============================================================
# TOOL ERRORS AND RESULTS
# ============================================================

class ToolError(DomainModel):
    """Safe error information returned by a tool."""

    code: ToolErrorCode
    message: str = Field(min_length=1, max_length=500)


class ToolSourceMetadata(DomainModel):
    """Metadata describing where tool data originated."""

    source_type: SourceType
    snapshot: bool = True
    latest_order_date: date | None = None
    document_section: str | None = None


T = TypeVar("T")


class ToolResult(DomainModel, Generic[T]):
    """Standard response envelope for application tools."""

    ok: bool
    tool_name: ToolName
    data: T | None = None
    error: ToolError | None = None
    source: ToolSourceMetadata | None = None

    @model_validator(mode="after")
    def validate_result(self):
        """Ensure successful and failed results are consistent."""

        if self.ok:
            if self.data is None:
                raise ValueError(
                    "A successful result must contain data."
                )

            if self.error is not None:
                raise ValueError(
                    "A successful result cannot contain an error."
                )

        else:
            if self.data is not None:
                raise ValueError(
                    "A failed result cannot contain data."
                )

            if self.error is None:
                raise ValueError(
                    "A failed result must contain an error."
                )

        return self


# ============================================================
# PRODUCT SEARCH
# ============================================================

class SearchProductsInput(DomainModel):
    """Parameters accepted by the product search tool."""

    query: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
    )

    category: str | None = Field(
        default=None,
        min_length=1,
        max_length=80,
    )

    min_price_brl: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        max_digits=12,
        decimal_places=2,
    )

    max_price_brl: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        max_digits=12,
        decimal_places=2,
    )

    availability: Literal[
        "available",
        "out_of_stock",
        "coming_soon",
        "discontinued",
        "all",
    ] = "available"

    sort_by: Literal[
        "price_asc",
        "price_desc",
        "name",
    ] = "price_asc"

    limit: int = Field(default=10, ge=1, le=10)

    @model_validator(mode="after")
    def validate_price_range(self):
        """Ensure the minimum price does not exceed the maximum."""

        if (
            self.min_price_brl is not None
            and self.max_price_brl is not None
            and self.min_price_brl > self.max_price_brl
        ):
            raise ValueError(
                "Minimum price cannot exceed maximum price."
            )

        return self


class ProductSummary(DomainModel):
    """Compact product representation for search results."""

    product_id: int = Field(gt=0)
    name: str
    price_cents: int = Field(ge=0)
    formatted_price: str
    stock_quantity: int = Field(ge=0)
    availability: ProductAvailability
    category: str


class ProductSearchData(DomainModel):
    """Data returned by product search."""

    total_matches: int = Field(ge=0)
    returned: int = Field(ge=0)
    truncated: bool
    products: list[ProductSummary]


# ============================================================
# PRODUCT DETAILS
# ============================================================

class GetProductDetailsInput(DomainModel):
    """Parameters accepted by the product details tool."""

    product_id: int = Field(gt=0)


class PromotionSummary(DomainModel):
    """Active promotion associated with a product."""

    promotion_id: int = Field(gt=0)
    description: str
    discount_percent: int = Field(gt=0, le=100)
    original_price_cents: int = Field(ge=0)
    promotional_price_cents: int = Field(ge=0)
    formatted_promotional_price: str


class ProductDetailsData(DomainModel):
    """Detailed product information."""

    product_id: int = Field(gt=0)
    name: str
    category: str
    status: ProductStatus
    availability: ProductAvailability

    price_cents: int = Field(ge=0)
    formatted_price: str

    stock_quantity: int = Field(ge=0)

    description: str
    specs: dict[str, str]
    created_at: date

    promotion: PromotionSummary | None = None


# ============================================================
# ORDER STATUS
# ============================================================

class GetOrderStatusInput(DomainModel):
    """Parameters accepted by the order status tool."""

    order_id: int = Field(gt=0)


class OrderItemSummary(DomainModel):
    """Product information associated with an order."""

    product_id: int = Field(gt=0)
    product_name: str
    quantity: int = Field(gt=0)


class OrderStatusData(DomainModel):
    """Information returned about an authorized order."""

    order_id: int = Field(gt=0)
    status: OrderStatus

    order_date: date

    tracking_code: str | None = None
    estimated_delivery: date | None = None

    items: list[OrderItemSummary]

    dataset_is_static: bool = True
    latest_order_date_in_dataset: date | None = None


# ============================================================
# INTERNAL ORDER VERIFICATION
# ============================================================

class OrderVerificationRequest(DomainModel):
    """
    Internal identity verification request.

    This model must never be exposed as an LLM tool
    or included in messages sent to the LLM provider.
    """

    order_id: int = Field(gt=0)
    phone: SecretStr

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, value):
        """Validate phone length without exposing the phone value."""

        if isinstance(value, SecretStr):
            value = value.get_secret_value()

        if not isinstance(value, str):
            raise ValueError("Phone must be a string.")

        digits = "".join(
            character
            for character in value
            if character.isdigit()
        )

        if not 8 <= len(digits) <= 15:
            raise ValueError("Invalid phone number length.")

        return SecretStr(value)


class OrderVerificationData(DomainModel):
    """Internal result of customer identity verification."""

    verified: bool
    authorized_order_id: int | None = None

    @model_validator(mode="after")
    def validate_authorization(self):
        if self.verified and self.authorized_order_id is None:
            raise ValueError(
                "Verified customers must have an authorized order."
            )

        if not self.verified and self.authorized_order_id is not None:
            raise ValueError(
                "Failed verification cannot authorize an order."
            )

        return self


# ============================================================
# POLICY RETRIEVAL
# ============================================================

class SearchStorePoliciesInput(DomainModel):
    """Parameters accepted by the policy retrieval tool."""

    query: str = Field(min_length=3, max_length=500)
    top_k: int = Field(default=3, ge=1, le=5)


class PolicyEvidence(DomainModel):
    """A retrieved passage from the store policy document."""

    section: str
    page: int = Field(gt=0)
    title: str
    content: str = Field(min_length=1)

    relevance_score: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )


class PolicySearchData(DomainModel):
    """Data returned by policy retrieval."""

    results: list[PolicyEvidence]
    requires_human_review: bool = False


# ============================================================
# STORE INFORMATION
# ============================================================

StoreInfoTopic = Literal[
    "address",
    "opening_hours",
    "contact",
    "payment_methods",
    "store_scope",
]


class GetStoreInformationInput(DomainModel):
    """Parameters accepted by the store information tool."""

    topic: StoreInfoTopic


class StoreInformationData(DomainModel):
    """Institutional information returned by the tool."""

    topic: StoreInfoTopic
    content: dict[str, Any]


# ============================================================
# PURCHASE CONDITIONS
# ============================================================

PaymentInquiryMethod = Literal[
    "pix",
    "credit",
    "debit",
    "boleto",
]


class GetPurchaseConditionsInput(DomainModel):
    """Parameters accepted by the purchase conditions tool."""

    product_id: int = Field(gt=0)

    payment_method: PaymentInquiryMethod

    installments: int | None = Field(
        default=None,
        ge=1,
        le=12,
    )

    @model_validator(mode="after")
    def validate_installments(self):
        """Installment count is only valid for credit card payments."""

        if (
            self.payment_method != "credit"
            and self.installments is not None
        ):
            raise ValueError(
                "Installments are only valid for credit payments."
            )

        return self


class PurchaseConditionsData(DomainModel):
    """Calculated purchase conditions."""

    product_id: int = Field(gt=0)

    list_price_cents: int = Field(ge=0)

    promotion: PromotionSummary | None = None

    payment_method: PaymentInquiryMethod

    discount_percent: int = Field(ge=0, le=100)
    discount_cents: int = Field(ge=0)

    final_price_cents: int = Field(ge=0)
    formatted_final_price: str

    installments: int | None = None
    installment_amounts_cents: list[int] = Field(
        default_factory=list
    )
