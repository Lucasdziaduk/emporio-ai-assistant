"""Create small CSV datasets for isolated loader tests."""

from __future__ import annotations

import csv
import json
from pathlib import Path


HEADERS = {
    "categories.csv": ["category_id", "name", "description"],
    "products.csv": ["product_id", "price_brl", "name", "category_id", "description", "stock_quantity", "status", "specs", "created_at"],
    "promotions.csv": ["promotion_id", "product_id", "discount_percent", "description", "is_active"],
    "customers.csv": ["customer_id", "name", "phone", "email", "city"],
    "orders.csv": ["order_id", "customer_id", "order_date", "status", "total_brl", "payment_method", "tracking_code", "estimated_delivery", "notes"],
    "order_items.csv": ["order_id", "quantity", "product_id"],
}


def write_dataset(directory: Path, *, invalid_order_customer: bool = False) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    rows = {
        "categories.csv": [
            {"category_id": 1, "name": "Violões", "description": "Violões clássicos e folk"}
        ],
        "products.csv": [
            {"product_id": 81, "price_brl": "10.50", "name": "Violão de teste", "category_id": 1,
             "description": "Produto fictício para testes", "stock_quantity": 3, "status": "active",
             "specs": json.dumps({"strings": "nylon"}), "created_at": "2025-01-10"}
        ],
        "promotions.csv": [
            {"promotion_id": 1, "product_id": 81, "discount_percent": 10,
             "description": "Promoção fictícia", "is_active": 1}
        ],
        "customers.csv": [
            {"customer_id": 1, "name": "Cliente Um", "phone": "(67) 90000-0001", "email": "same@example.test", "city": "Campo Grande"},
            {"customer_id": 2, "name": "Cliente Dois", "phone": "(67) 90000-0002", "email": "SAME@example.test", "city": "Dourados"},
        ],
        "orders.csv": [
            {"order_id": 1, "customer_id": 999 if invalid_order_customer else 1, "order_date": "2026-01-10",
             "status": "delivered", "total_brl": "9.50", "payment_method": "pix",
             "tracking_code": "", "estimated_delivery": "", "notes": ""}
        ],
        "order_items.csv": [
            {"order_id": 1, "quantity": 1, "product_id": 81}
        ],
    }

    for filename, records in rows.items():
        with (directory / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=HEADERS[filename])
            writer.writeheader()
            writer.writerows(records)
    return directory
