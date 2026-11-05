"""SQLite database creation and schema management."""

from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
    name TEXT NOT NULL,
    category_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0),
    status TEXT NOT NULL CHECK (
        status IN ('active', 'discontinued', 'coming_soon')
    ),
    specs_json TEXT NOT NULL CHECK (json_valid(specs_json)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

CREATE TABLE IF NOT EXISTS promotions (
    promotion_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    discount_percent INTEGER NOT NULL CHECK (
        discount_percent BETWEEN 1 AND 100
    ),
    description TEXT NOT NULL,
    is_active INTEGER NOT NULL CHECK (is_active IN (0, 1)),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    city TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')
    ),
    total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
    payment_method TEXT NOT NULL CHECK (
        payment_method IN ('pix', 'debit', 'boleto', 'credit_3x', 'credit_6x', 'credit_12x')
    ),
    tracking_code TEXT,
    estimated_delivery TEXT,
    notes TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS order_items (
    order_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    product_id INTEGER NOT NULL,
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS dataset_metadata (
    dataset_id INTEGER PRIMARY KEY CHECK (dataset_id = 1),
    loaded_at_utc TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    table_counts_json TEXT NOT NULL CHECK (json_valid(table_counts_json)),
    source_hashes_json TEXT NOT NULL CHECK (json_valid(source_hashes_json)),
    earliest_order_date TEXT,
    latest_order_date TEXT
);

CREATE TABLE IF NOT EXISTS data_quality_issues (
    issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'error')),
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    message TEXT NOT NULL,
    detected_at_utc TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_products_category
    ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_status_stock
    ON products(status, stock_quantity);
CREATE INDEX IF NOT EXISTS idx_promotions_product_active
    ON promotions(product_id, is_active);
CREATE INDEX IF NOT EXISTS idx_orders_customer
    ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status
    ON orders(status);
CREATE INDEX IF NOT EXISTS idx_order_items_product
    ON order_items(product_id);
"""


def create_connection(database: str | Path = ":memory:") -> sqlite3.Connection:
    """Create a SQLite connection with row access and FK enforcement."""

    database_value = str(database)
    if database_value != ":memory:":
        Path(database_value).parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_value)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create all tables and indexes if they do not already exist."""

    connection.executescript(SCHEMA_SQL)
    connection.commit()


def foreign_key_violations(
    connection: sqlite3.Connection,
) -> list[sqlite3.Row]:
    """Return SQLite foreign-key violations (empty means valid)."""

    return list(connection.execute("PRAGMA foreign_key_check").fetchall())
