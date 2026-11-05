import sqlite3

from app.data.database import create_connection, foreign_key_violations, initialize_database


def test_database_enables_foreign_keys_and_creates_tables():
    connection = create_connection()
    initialize_database(connection)

    foreign_keys_enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]
    table_names = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }

    assert foreign_keys_enabled == 1
    assert {"categories", "products", "promotions", "customers", "orders", "order_items"}.issubset(table_names)
    assert "dataset_metadata" in table_names
    assert "data_quality_issues" in table_names
    assert foreign_key_violations(connection) == []
    connection.close()


def test_database_rejects_invalid_foreign_key():
    connection = create_connection()
    initialize_database(connection)
    connection.execute(
        "INSERT INTO categories(category_id, name, description) VALUES (1, 'Test', 'Test')"
    )
    try:
        connection.execute(
            """INSERT INTO products(
                product_id, price_cents, name, category_id, description,
                stock_quantity, status, specs_json, created_at
            ) VALUES (1, 100, 'Product', 999, 'Description', 1, 'active', '{}', '2025-01-01')"""
        )
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("SQLite should reject an invalid category foreign key.")
    connection.close()
