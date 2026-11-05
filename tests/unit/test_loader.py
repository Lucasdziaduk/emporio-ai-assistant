import sqlite3

import pytest

from app.data.database import create_connection
from app.data.loader import DataValidationError, MissingDataFileError, load_dataset, money_to_cents
from app.data.repositories import DatasetRepository, OrderRepository, ProductRepository
from tests.fixtures.dataset_factory import write_dataset


def test_money_to_cents_uses_decimal_exactly():
    assert money_to_cents("599.9") == 59990
    assert money_to_cents("11499") == 1149900
    assert money_to_cents("0.01") == 1


def test_money_to_cents_rejects_more_than_two_decimal_places():
    with pytest.raises(DataValidationError):
        money_to_cents("10.001")


def test_load_dataset_ingests_records_and_audits_duplicate_email(tmp_path):
    source = write_dataset(tmp_path / "source")
    connection = create_connection()

    report = load_dataset(source, connection)

    assert report.table_counts == {
        "categories": 1,
        "products": 1,
        "promotions": 1,
        "customers": 2,
        "orders": 1,
        "order_items": 1,
    }
    assert report.earliest_order_date == "2026-01-10"
    assert report.latest_order_date == "2026-01-10"
    assert any(issue.code == "DUPLICATE_CUSTOMER_EMAIL" for issue in report.issues)

    product = ProductRepository(connection).get_by_id(81)
    assert product is not None
    assert product.price_cents == 1050
    assert product.availability.value == "available"

    order = OrderRepository(connection).get_by_id(1)
    assert order is not None
    assert order.total_cents == 950
    assert OrderRepository(connection).get_items(1)[0].quantity == 1

    metadata = DatasetRepository(connection).get_metadata()
    assert metadata is not None
    assert metadata["table_counts"]["products"] == 1
    connection.close()


def test_load_dataset_rejects_bad_foreign_key_before_replacing_existing_data(tmp_path):
    valid_source = write_dataset(tmp_path / "valid")
    invalid_source = write_dataset(tmp_path / "invalid", invalid_order_customer=True)
    connection = create_connection()
    load_dataset(valid_source, connection)

    with pytest.raises(DataValidationError, match="orders.customer_id"):
        load_dataset(invalid_source, connection)

    assert connection.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 1
    connection.close()


def test_load_dataset_is_repeatable(tmp_path):
    source = write_dataset(tmp_path / "source")
    connection = create_connection()

    load_dataset(source, connection)
    load_dataset(source, connection)

    assert connection.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 1
    connection.close()


def test_missing_file_has_clear_error(tmp_path):
    source = write_dataset(tmp_path / "source")
    (source / "orders.csv").unlink()
    connection = create_connection()

    with pytest.raises(MissingDataFileError, match="orders.csv"):
        load_dataset(source, connection)
    connection.close()


def test_invalid_enum_is_rejected(tmp_path):
    source = write_dataset(tmp_path / "source")
    products_path = source / "products.csv"
    content = products_path.read_text(encoding="utf-8")
    products_path.write_text(content.replace(",active,", ",invalid_status,"), encoding="utf-8")
    connection = create_connection()

    with pytest.raises(DataValidationError, match="invalid 'status'"):
        load_dataset(source, connection)
    connection.close()


def test_empty_optional_order_fields_become_null(tmp_path):
    source = write_dataset(tmp_path / "source")
    connection = create_connection()
    load_dataset(source, connection)

    row = connection.execute(
        "SELECT tracking_code, estimated_delivery, notes FROM orders WHERE order_id = 1"
    ).fetchone()
    assert row["tracking_code"] is None
    assert row["estimated_delivery"] is None
    assert row["notes"] is None
    connection.close()


def test_load_report_persists_quality_issues(tmp_path):
    source = write_dataset(tmp_path / "source")
    connection = create_connection()
    report = load_dataset(source, connection)

    persisted = connection.execute(
        "SELECT code FROM data_quality_issues ORDER BY code"
    ).fetchall()
    assert len(persisted) == report.warning_count
    assert {row["code"] for row in persisted} == {
        "DUPLICATE_CUSTOMER_EMAIL",
        "ORDER_TOTAL_DIFFERS_FROM_CURRENT_CATALOG",
    }
    connection.close()


def test_failed_reload_keeps_previous_snapshot_intact(tmp_path):
    valid_source = write_dataset(tmp_path / "valid")
    invalid_source = write_dataset(tmp_path / "invalid", invalid_order_customer=True)
    connection = create_connection()
    initial_report = load_dataset(valid_source, connection)

    with pytest.raises(DataValidationError):
        load_dataset(invalid_source, connection)

    metadata = connection.execute(
        "SELECT loaded_at_utc FROM dataset_metadata WHERE dataset_id = 1"
    ).fetchone()
    assert metadata["loaded_at_utc"] == initial_report.loaded_at_utc
    assert connection.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 1
    connection.close()
