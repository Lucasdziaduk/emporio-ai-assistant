
"""Core domain models for the Emporio AI Assistant."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.domain.enums import OrderStatus, PaymentMethod, ProductAvailability, ProductStatus


class DomainModel(BaseModel):
    """Base model with shared validation configuration."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class Category(DomainModel):
    """Product category."""

    category_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class Product(DomainModel):
    """Product registered in the store catalog."""

    product_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    price_cents: int = Field(ge=0)
    category_id: int = Field(gt=0)
    description: str = Field(min_length=1)
    stock_quantity: int = Field(ge=0)
    status: ProductStatus
    specs: dict[str, str] = Field(default_factory=dict)
    created_at: date

    @computed_field
    @property
    def availability(self) -> ProductAvailability:
        """Calculate product availability from status and stock."""

        if self.status == ProductStatus.DISCONTINUED:
            return ProductAvailability.DISCONTINUED

        if self.status == ProductStatus.COMING_SOON:
            return ProductAvailability.COMING_SOON

        if self.stock_quantity == 0:
            return ProductAvailability.OUT_OF_STOCK

        return ProductAvailability.AVAILABLE


class Promotion(DomainModel):
    """Promotional offer associated with a product."""

    promotion_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    discount_percent: int = Field(gt=0, le=100)
    description: str = Field(min_length=1)
    is_active: bool


class Customer(DomainModel):
    """Customer registered in the supplied dataset."""

    customer_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    email: str | None = None
    city: str = Field(min_length=1)


class Order(DomainModel):
    """Customer order."""

    order_id: int = Field(gt=0)
    customer_id: int = Field(gt=0)
    order_date: date
    status: OrderStatus
    total_cents: int = Field(ge=0)
    payment_method: PaymentMethod
    tracking_code: str | None = None
    estimated_delivery: date | None = None
    notes: str | None = None


class OrderItem(DomainModel):
    """Product associated with an order."""

    order_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
