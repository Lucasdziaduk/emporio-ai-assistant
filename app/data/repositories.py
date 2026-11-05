"""Read-only repositories that map SQLite rows to domain models."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.domain.models import Category, Customer, Order, OrderItem, Product, Promotion


def _dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


class CategoryRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get_by_id(self, category_id: int) -> Category | None:
        row = self.connection.execute(
            "SELECT category_id, name, description FROM categories WHERE category_id = ?",
            (category_id,),
        ).fetchone()
        return Category.model_validate(_dict(row)) if row else None

    def list_all(self) -> list[Category]:
        rows = self.connection.execute(
            "SELECT category_id, name, description FROM categories ORDER BY name"
        ).fetchall()
        return [Category.model_validate(dict(row)) for row in rows]


class ProductRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    @staticmethod
    def _to_model(row: sqlite3.Row) -> Product:
        data = dict(row)
        data["specs"] = json.loads(data.pop("specs_json"))
        return Product.model_validate(data)

    def get_by_id(self, product_id: int) -> Product | None:
        row = self.connection.execute(
            "SELECT * FROM products WHERE product_id = ?", (product_id,)
        ).fetchone()
        return self._to_model(row) if row else None

    def list_all(self, *, limit: int = 1000) -> list[Product]:
        if not 1 <= limit <= 5000:
            raise ValueError("limit must be between 1 and 5000")
        rows = self.connection.execute(
            "SELECT * FROM products ORDER BY product_id LIMIT ?", (limit,)
        ).fetchall()
        return [self._to_model(row) for row in rows]


class PromotionRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    @staticmethod
    def _to_model(row: sqlite3.Row) -> Promotion:
        return Promotion.model_validate(dict(row))

    def get_by_id(self, promotion_id: int) -> Promotion | None:
        row = self.connection.execute(
            "SELECT * FROM promotions WHERE promotion_id = ?", (promotion_id,)
        ).fetchone()
        return self._to_model(row) if row else None

    def list_active_for_product(self, product_id: int) -> list[Promotion]:
        rows = self.connection.execute(
            """SELECT * FROM promotions
               WHERE product_id = ? AND is_active = 1
               ORDER BY promotion_id""",
            (product_id,),
        ).fetchall()
        return [self._to_model(row) for row in rows]


class CustomerRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get_by_id(self, customer_id: int) -> Customer | None:
        row = self.connection.execute(
            "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
        ).fetchone()
        return Customer.model_validate(_dict(row)) if row else None




class OrderRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get_by_id(self, order_id: int) -> Order | None:
        row = self.connection.execute(
            "SELECT * FROM orders WHERE order_id = ?", (order_id,)
        ).fetchone()
        return Order.model_validate(_dict(row)) if row else None

    def get_items(self, order_id: int) -> list[OrderItem]:
        rows = self.connection.execute(
            """SELECT order_id, product_id, quantity
               FROM order_items WHERE order_id = ?
               ORDER BY product_id""",
            (order_id,),
        ).fetchall()
        return [OrderItem.model_validate(dict(row)) for row in rows]

    def get_customer_id(self, order_id: int) -> int | None:
        row = self.connection.execute(
            "SELECT customer_id FROM orders WHERE order_id = ?", (order_id,)
        ).fetchone()
        return int(row["customer_id"]) if row else None


class DatasetRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get_metadata(self) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM dataset_metadata WHERE dataset_id = 1"
        ).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["table_counts"] = json.loads(data.pop("table_counts_json"))
        data["source_hashes"] = json.loads(data.pop("source_hashes_json"))
        return data

    def list_quality_issues(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """SELECT code, severity, entity_type, entity_id, message, detected_at_utc
               FROM data_quality_issues ORDER BY issue_id"""
        ).fetchall()
        return [dict(row) for row in rows]
