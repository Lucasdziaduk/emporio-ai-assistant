
"""Enumerations used throughout the application."""

from enum import Enum


class ProductStatus(str, Enum):
    """Commercial status of a product in the catalog."""

    ACTIVE = "active"
    DISCONTINUED = "discontinued"
    COMING_SOON = "coming_soon"


class ProductAvailability(str, Enum):
    """Availability derived from status and stock quantity."""

    AVAILABLE = "available"
    OUT_OF_STOCK = "out_of_stock"
    COMING_SOON = "coming_soon"
    DISCONTINUED = "discontinued"


class AvailabilityFilter(str, Enum):
    """Availability filters accepted by catalog searches."""

    AVAILABLE = "available"
    OUT_OF_STOCK = "out_of_stock"
    COMING_SOON = "coming_soon"
    DISCONTINUED = "discontinued"
    ALL = "all"


class OrderStatus(str, Enum):
    """Possible order statuses in the supplied dataset."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    """Payment methods found in the supplied dataset."""

    PIX = "pix"
    DEBIT = "debit"
    BOLETO = "boleto"
    CREDIT_3X = "credit_3x"
    CREDIT_6X = "credit_6x"
    CREDIT_12X = "credit_12x"
