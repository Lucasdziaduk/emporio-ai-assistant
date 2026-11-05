"""CSV ingestion, normalization, validation, and dataset auditing."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.domain.enums import OrderStatus, PaymentMethod, ProductStatus
from app.data.database import initialize_database


CSV_COLUMNS: dict[str, tuple[str, ...]] = {
    "categories.csv": ("category_id", "name", "description"),
    "products.csv": (
        "product_id", "price_brl", "name", "category_id", "description",
        "stock_quantity", "status", "specs", "created_at",
    ),
    "promotions.csv": (
        "promotion_id", "product_id", "discount_percent", "description", "is_active",
    ),
    "customers.csv": ("customer_id", "name", "phone", "email", "city"),
    "orders.csv": (
        "order_id", "customer_id", "order_date", "status", "total_brl",
        "payment_method", "tracking_code", "estimated_delivery", "notes",
    ),
    "order_items.csv": ("order_id", "quantity", "product_id"),
}

TABLE_ORDER = (
    "categories", "products", "promotions", "customers", "orders", "order_items"
)


class DataLoadError(Exception):
    """Raised when source data is missing or cannot be safely ingested."""


class MissingDataFileError(DataLoadError):
    """Raised when one or more required CSV files are missing."""


class DataValidationError(DataLoadError):
    """Raised when source data violates the declared data contract."""


@dataclass(frozen=True)
class DataQualityIssue:
    code: str
    severity: str
    entity_type: str
    entity_id: str | None
    message: str


@dataclass(frozen=True)
class LoadReport:
    loaded_at_utc: str
    table_counts: dict[str, int]
    source_hashes: dict[str, str]
    earliest_order_date: str | None
    latest_order_date: str | None
    issues: tuple[DataQualityIssue, ...]

    @property
    def warning_count(self) -> int:
        return sum(issue.severity == "warning" for issue in self.issues)


def _required_text(value: str | None, *, file: str, row: int, field: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise DataValidationError(
            f"{file}, row {row}: required field {field!r} is empty."
        )
    return normalized


def _optional_text(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def _integer(
    value: str | None,
    *,
    file: str,
    row: int,
    field: str,
    minimum: int | None = None,
) -> int:
    raw = _required_text(value, file=file, row=row, field=field)
    try:
        parsed = int(raw)
    except ValueError as exc:
        raise DataValidationError(
            f"{file}, row {row}: field {field!r} must be an integer."
        ) from exc
    if minimum is not None and parsed < minimum:
        raise DataValidationError(
            f"{file}, row {row}: field {field!r} must be >= {minimum}."
        )
    return parsed


def money_to_cents(
    value: str | int | Decimal,
    *,
    file: str = "<value>",
    row: int = 0,
    field: str = "amount",
) -> int:
    """Convert a BRL amount to integer cents without float arithmetic."""

    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError) as exc:
        raise DataValidationError(
            f"{file}, row {row}: field {field!r} is not a valid decimal amount."
        ) from exc

    if not amount.is_finite() or amount < 0:
        raise DataValidationError(
            f"{file}, row {row}: field {field!r} must be a finite, non-negative amount."
        )

    cents = amount * Decimal("100")
    if cents != cents.to_integral_value():
        raise DataValidationError(
            f"{file}, row {row}: field {field!r} has more than two decimal places."
        )
    return int(cents)


def _date(
    value: str | None,
    *,
    file: str,
    row: int,
    field: str,
    optional: bool = False,
) -> str | None:
    raw = _optional_text(value) if optional else _required_text(
        value, file=file, row=row, field=field
    )
    if raw is None:
        return None
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise DataValidationError(
            f"{file}, row {row}: field {field!r} must use YYYY-MM-DD."
        ) from exc


def _enum_value(enum_type: type, value: str | None, *, file: str, row: int, field: str) -> str:
    raw = _required_text(value, file=file, row=row, field=field)
    try:
        return enum_type(raw).value
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise DataValidationError(
            f"{file}, row {row}: invalid {field!r} value {raw!r}; allowed: {allowed}."
        ) from exc


def _boolean_01(value: str | None, *, file: str, row: int, field: str) -> int:
    raw = _required_text(value, file=file, row=row, field=field)
    if raw not in {"0", "1"}:
        raise DataValidationError(
            f"{file}, row {row}: field {field!r} must be 0 or 1."
        )
    return int(raw)


def _json_object(value: str | None, *, file: str, row: int, field: str) -> tuple[str, dict[str, str]]:
    raw = _required_text(value, file=file, row=row, field=field)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DataValidationError(
            f"{file}, row {row}: field {field!r} contains invalid JSON."
        ) from exc
    if not isinstance(parsed, dict) or not all(
        isinstance(key, str) and isinstance(item, str)
        for key, item in parsed.items()
    ):
        raise DataValidationError(
            f"{file}, row {row}: field {field!r} must be a JSON object of string values."
        )
    return json.dumps(parsed, ensure_ascii=False, sort_keys=True), parsed


def _read_csv(source_dir: Path, filename: str) -> tuple[list[dict[str, str]], str]:
    path = source_dir / filename
    if not path.is_file():
        raise MissingDataFileError(f"Required source file not found: {filename}")

    raw_bytes = path.read_bytes()
    digest = hashlib.sha256(raw_bytes).hexdigest()
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DataValidationError(f"{filename}: file must be UTF-8 encoded.") from exc

    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames is None:
        raise DataValidationError(f"{filename}: CSV has no header.")

    missing = sorted(set(CSV_COLUMNS[filename]) - set(reader.fieldnames))
    if missing:
        raise DataValidationError(
            f"{filename}: missing required columns: {', '.join(missing)}."
        )

    rows = []
    for line_number, raw_row in enumerate(reader, start=2):
        if None in raw_row:
            raise DataValidationError(
                f"{filename}, row {line_number}: row contains more values than the header."
            )
        rows.append({key: (value or "") for key, value in raw_row.items()})

    if not rows:
        raise DataValidationError(f"{filename}: file contains no data rows.")
    return rows, digest


def _parse_dataset(source_dir: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str]]:
    raw: dict[str, list[dict[str, str]]] = {}
    hashes: dict[str, str] = {}
    for filename in CSV_COLUMNS:
        raw[filename], hashes[filename] = _read_csv(source_dir, filename)

    parsed: dict[str, list[dict[str, Any]]] = {}

    rows = raw["categories.csv"]
    parsed["categories"] = [
        {
            "category_id": _integer(r["category_id"], file="categories.csv", row=i, field="category_id", minimum=1),
            "name": _required_text(r["name"], file="categories.csv", row=i, field="name"),
            "description": _required_text(r["description"], file="categories.csv", row=i, field="description"),
        }
        for i, r in enumerate(rows, start=2)
    ]

    rows = raw["products.csv"]
    parsed["products"] = []
    for i, r in enumerate(rows, start=2):
        specs_json, _ = _json_object(r["specs"], file="products.csv", row=i, field="specs")
        parsed["products"].append({
            "product_id": _integer(r["product_id"], file="products.csv", row=i, field="product_id", minimum=1),
            "price_cents": money_to_cents(r["price_brl"], file="products.csv", row=i, field="price_brl"),
            "name": _required_text(r["name"], file="products.csv", row=i, field="name"),
            "category_id": _integer(r["category_id"], file="products.csv", row=i, field="category_id", minimum=1),
            "description": _required_text(r["description"], file="products.csv", row=i, field="description"),
            "stock_quantity": _integer(r["stock_quantity"], file="products.csv", row=i, field="stock_quantity", minimum=0),
            "status": _enum_value(ProductStatus, r["status"], file="products.csv", row=i, field="status"),
            "specs_json": specs_json,
            "created_at": _date(r["created_at"], file="products.csv", row=i, field="created_at"),
        })

    rows = raw["promotions.csv"]
    parsed["promotions"] = [
        {
            "promotion_id": _integer(r["promotion_id"], file="promotions.csv", row=i, field="promotion_id", minimum=1),
            "product_id": _integer(r["product_id"], file="promotions.csv", row=i, field="product_id", minimum=1),
            "discount_percent": _integer(r["discount_percent"], file="promotions.csv", row=i, field="discount_percent", minimum=1),
            "description": _required_text(r["description"], file="promotions.csv", row=i, field="description"),
            "is_active": _boolean_01(r["is_active"], file="promotions.csv", row=i, field="is_active"),
        }
        for i, r in enumerate(rows, start=2)
    ]

    rows = raw["customers.csv"]
    parsed["customers"] = [
        {
            "customer_id": _integer(r["customer_id"], file="customers.csv", row=i, field="customer_id", minimum=1),
            "name": _required_text(r["name"], file="customers.csv", row=i, field="name"),
            "phone": _required_text(r["phone"], file="customers.csv", row=i, field="phone"),
            "email": _optional_text(r["email"]),
            "city": _required_text(r["city"], file="customers.csv", row=i, field="city"),
        }
        for i, r in enumerate(rows, start=2)
    ]

    rows = raw["orders.csv"]
    parsed["orders"] = []
    for i, r in enumerate(rows, start=2):
        parsed["orders"].append({
            "order_id": _integer(r["order_id"], file="orders.csv", row=i, field="order_id", minimum=1),
            "customer_id": _integer(r["customer_id"], file="orders.csv", row=i, field="customer_id", minimum=1),
            "order_date": _date(r["order_date"], file="orders.csv", row=i, field="order_date"),
            "status": _enum_value(OrderStatus, r["status"], file="orders.csv", row=i, field="status"),
            "total_cents": money_to_cents(r["total_brl"], file="orders.csv", row=i, field="total_brl"),
            "payment_method": _enum_value(PaymentMethod, r["payment_method"], file="orders.csv", row=i, field="payment_method"),
            "tracking_code": _optional_text(r["tracking_code"]),
            "estimated_delivery": _date(r["estimated_delivery"], file="orders.csv", row=i, field="estimated_delivery", optional=True),
            "notes": _optional_text(r["notes"]),
        })

    rows = raw["order_items.csv"]
    parsed["order_items"] = [
        {
            "order_id": _integer(r["order_id"], file="order_items.csv", row=i, field="order_id", minimum=1),
            "quantity": _integer(r["quantity"], file="order_items.csv", row=i, field="quantity", minimum=1),
            "product_id": _integer(r["product_id"], file="order_items.csv", row=i, field="product_id", minimum=1),
        }
        for i, r in enumerate(rows, start=2)
    ]

    _validate_primary_keys(parsed)
    _validate_foreign_keys(parsed)
    return parsed, hashes


def _validate_unique(values: list[Any], label: str) -> None:
    seen: set[Any] = set()
    duplicates: set[Any] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        preview = ", ".join(str(value) for value in sorted(duplicates)[:10])
        raise DataValidationError(f"Duplicate primary/composite keys in {label}: {preview}.")


def _validate_primary_keys(data: dict[str, list[dict[str, Any]]]) -> None:
    for table, key in (
        ("categories", "category_id"),
        ("products", "product_id"),
        ("promotions", "promotion_id"),
        ("customers", "customer_id"),
        ("orders", "order_id"),
    ):
        _validate_unique([row[key] for row in data[table]], f"{table}.{key}")

    _validate_unique(
        [(row["order_id"], row["product_id"]) for row in data["order_items"]],
        "order_items(order_id, product_id)",
    )


def _validate_foreign_keys(data: dict[str, list[dict[str, Any]]]) -> None:
    category_ids = {row["category_id"] for row in data["categories"]}
    product_ids = {row["product_id"] for row in data["products"]}
    customer_ids = {row["customer_id"] for row in data["customers"]}
    order_ids = {row["order_id"] for row in data["orders"]}

    checks = (
        ("products.category_id", ((r["category_id"], r["product_id"]) for r in data["products"]), category_ids),
        ("promotions.product_id", ((r["product_id"], r["promotion_id"]) for r in data["promotions"]), product_ids),
        ("orders.customer_id", ((r["customer_id"], r["order_id"]) for r in data["orders"]), customer_ids),
        ("order_items.order_id", ((r["order_id"], r["order_id"]) for r in data["order_items"]), order_ids),
        ("order_items.product_id", ((r["product_id"], r["order_id"]) for r in data["order_items"]), product_ids),
    )
    for label, pairs, valid_ids in checks:
        invalid = [(foreign_id, row_id) for foreign_id, row_id in pairs if foreign_id not in valid_ids]
        if invalid:
            preview = ", ".join(f"row {row_id} -> {foreign_id}" for foreign_id, row_id in invalid[:10])
            raise DataValidationError(f"Invalid foreign keys in {label}: {preview}.")


def _audit_data(data: dict[str, list[dict[str, Any]]]) -> tuple[DataQualityIssue, ...]:
    issues: list[DataQualityIssue] = []
    emails: dict[str, list[int]] = defaultdict(list)
    for customer in data["customers"]:
        email = (customer["email"] or "").strip().casefold()
        if email:
            emails[email].append(customer["customer_id"])
    for customer_ids in emails.values():
        if len(customer_ids) > 1:
            ids = sorted(customer_ids)
            issues.append(DataQualityIssue(
                code="DUPLICATE_CUSTOMER_EMAIL",
                severity="warning",
                entity_type="customers",
                entity_id=",".join(map(str, ids)),
                message=(
                    "The same email is associated with multiple customer records "
                    f"(customer IDs: {', '.join(map(str, ids))}). Email is not used as a unique key."
                ),
            ))

    active_promotions: dict[int, list[int]] = defaultdict(list)
    for promotion in data["promotions"]:
        if promotion["is_active"] == 1:
            active_promotions[promotion["product_id"]].append(promotion["promotion_id"])
    for product_id, promotion_ids in active_promotions.items():
        if len(promotion_ids) > 1:
            issues.append(DataQualityIssue(
                code="MULTIPLE_ACTIVE_PROMOTIONS",
                severity="warning",
                entity_type="products",
                entity_id=str(product_id),
                message=(
                    f"Product {product_id} has multiple active promotions "
                    f"(promotion IDs: {', '.join(map(str, sorted(promotion_ids)))}). "
                    "The application must not choose one arbitrarily."
                ),
            ))

    product_prices = {row["product_id"]: row["price_cents"] for row in data["products"]}
    items_by_order: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in data["order_items"]:
        items_by_order[item["order_id"]].append(item)

    for order in data["orders"]:
        current_catalog_subtotal = sum(
            product_prices[item["product_id"]] * item["quantity"]
            for item in items_by_order.get(order["order_id"], [])
        )
        if current_catalog_subtotal != order["total_cents"]:
            difference = order["total_cents"] - current_catalog_subtotal
            issues.append(DataQualityIssue(
                code="ORDER_TOTAL_DIFFERS_FROM_CURRENT_CATALOG",
                severity="warning",
                entity_type="orders",
                entity_id=str(order["order_id"]),
                message=(
                    f"Order {order['order_id']} total differs from the subtotal calculated "
                    "with current catalog prices. The recorded order total was preserved; "
                    f"difference in cents: {difference}. This may reflect historical pricing or discounts."
                ),
            ))

    # The loader assigns one common timestamp when persisting the report.
    return tuple(issues)


def _insert_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    columns = tuple(rows[0].keys())
    placeholders = ", ".join("?" for _ in columns)
    column_sql = ", ".join(columns)
    sql = f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})"
    connection.executemany(sql, [tuple(row[column] for column in columns) for row in rows])


def load_dataset(
    source_dir: str | Path,
    connection: sqlite3.Connection,
    *,
    replace_existing: bool = True,
) -> LoadReport:
    """Validate and atomically load the six required CSV files into SQLite.

    Parsing, schema checks, key checks, and cross-file checks happen before
    modifying the database. Existing data is replaced atomically by default.
    """

    directory = Path(source_dir).expanduser().resolve()
    if not directory.is_dir():
        raise MissingDataFileError(f"Source directory does not exist: {directory}")

    parsed, source_hashes = _parse_dataset(directory)
    issues = _audit_data(parsed)
    loaded_at = datetime.now(timezone.utc).isoformat()

    initialize_database(connection)

    if not replace_existing:
        existing = connection.execute(
            "SELECT 1 FROM dataset_metadata WHERE dataset_id = 1"
        ).fetchone()
        if existing:
            raise DataLoadError("A dataset is already loaded and replace_existing=False.")

    table_counts = {table: len(parsed[table]) for table in TABLE_ORDER}
    order_dates = sorted(row["order_date"] for row in parsed["orders"])

    try:
        connection.execute("BEGIN IMMEDIATE")
        if replace_existing:
            for table in (
                "order_items", "orders", "promotions", "products", "customers",
                "categories", "data_quality_issues", "dataset_metadata",
            ):
                connection.execute(f"DELETE FROM {table}")

        for table in TABLE_ORDER:
            _insert_rows(connection, table, parsed[table])

        connection.execute(
            """INSERT INTO dataset_metadata (
                dataset_id, loaded_at_utc, source_kind, table_counts_json,
                source_hashes_json, earliest_order_date, latest_order_date
            ) VALUES (1, ?, 'static_csv_snapshot', ?, ?, ?, ?)""",
            (
                loaded_at,
                json.dumps(table_counts, sort_keys=True),
                json.dumps(source_hashes, sort_keys=True),
                order_dates[0] if order_dates else None,
                order_dates[-1] if order_dates else None,
            ),
        )

        connection.executemany(
            """INSERT INTO data_quality_issues (
                code, severity, entity_type, entity_id, message, detected_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (issue.code, issue.severity, issue.entity_type, issue.entity_id,
                 issue.message, loaded_at)
                for issue in issues
            ],
        )

        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise DataValidationError(
                f"SQLite reported {len(violations)} foreign-key violation(s) after loading."
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    return LoadReport(
        loaded_at_utc=loaded_at,
        table_counts=table_counts,
        source_hashes=source_hashes,
        earliest_order_date=order_dates[0] if order_dates else None,
        latest_order_date=order_dates[-1] if order_dates else None,
        issues=issues,
    )
