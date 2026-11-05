"""Read-only order lookup guarded by a local identity grant."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from app.data.repositories import DatasetRepository, OrderRepository, ProductRepository
from app.domain.errors import AuthenticationRequiredError, NotFoundError
from app.domain.schemas import OrderItemSummary, OrderStatusData

if TYPE_CHECKING:
    from app.services.identity_service import OrderAccessGrant


class OrderService:
    """Retrieve order details only after validating an IdentityService grant."""

    def __init__(
        self,
        order_repository: OrderRepository,
        product_repository: ProductRepository,
        dataset_repository: DatasetRepository,
    ) -> None:
        self.order_repository = order_repository
        self.product_repository = product_repository
        self.dataset_repository = dataset_repository

    def get_order_status(
        self,
        order_id: int,
        *,
        authorization: OrderAccessGrant | None,
        session_id: str,
        now: datetime | None = None,
    ) -> OrderStatusData:
        """Return the minimum order details needed for a customer response."""
        if authorization is None or not authorization.is_valid_for(
            order_id, session_id, now=now
        ):
            raise AuthenticationRequiredError()

        order = self.order_repository.get_by_id(order_id)
        if order is None:
            raise NotFoundError()

        item_summaries: list[OrderItemSummary] = []
        for item in self.order_repository.get_items(order_id):
            product = self.product_repository.get_by_id(item.product_id)
            item_summaries.append(
                OrderItemSummary(
                    product_id=item.product_id,
                    product_name=product.name if product else f"Produto {item.product_id}",
                    quantity=item.quantity,
                )
            )

        metadata = self.dataset_repository.get_metadata() or {}
        latest_raw = metadata.get("latest_order_date")
        latest_date = date.fromisoformat(latest_raw) if latest_raw else None

        # This is a static snapshot. The estimated delivery date is preserved
        # as recorded, but must never be described as a current live ETA.
        return OrderStatusData(
            order_id=order.order_id,
            status=order.status,
            order_date=order.order_date,
            tracking_code=order.tracking_code,
            estimated_delivery=order.estimated_delivery,
            items=item_summaries,
            dataset_is_static=True,
            latest_order_date_in_dataset=latest_date,
        )
