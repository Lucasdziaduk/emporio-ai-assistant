# M2 — Data Layer (SQLite + CSV Loader)

This overlay implements the project's data layer. It intentionally does **not** include the challenge's source CSVs, customer records, or restricted policy PDF.

## Files added

- `app/data/database.py`: SQLite schema, connection setup, foreign-key enforcement.
- `app/data/loader.py`: CSV parsing, strict type conversion, cross-file validation, atomic load, data-quality audit, dataset hashes and metadata.
- `app/data/repositories.py`: read-only repositories mapping database rows to Pydantic domain models.
- `app/data/__main__.py`: command-line entry point for loading and auditing the supplied dataset.
- `tests/unit/`: automated tests using synthetic records only.

## Required source files

Place the six original CSV files in:

```text
data/private/source/
```

Rename them exactly as follows (the ZIP's original filenames have an extra prefix):

```text
products.csv
categories.csv
promotions.csv
customers.csv
orders.csv
order_items.csv
```

Keep `data/private/` out of Git. The repository's `.gitignore` already ignores this directory.

## Load and audit the real dataset

From the project root, with the virtual environment active:

```powershell
python -m app.data
```

The command loads the six CSVs into an in-memory SQLite database and prints a JSON report containing counts, date range and data-quality warnings. The database exists only for that process; later application startup will create and load its own connection.

## Run automated tests

```powershell
python -m pytest tests/unit -v
```

Tests use generated synthetic CSVs and do not need the original challenge files or Gemini API key.

## Data handling decisions

- `price_brl` and `total_brl` are parsed as `Decimal` reais and converted to integer cents. No binary floating-point arithmetic is used for money.
- Empty optional CSV fields become SQL `NULL`.
- Product specifications are validated as JSON objects with string keys and values.
- Primary keys, composite order-item keys, enum values, and foreign-key relationships are validated before any existing database contents are replaced.
- Loading is transactional. Invalid source data is rejected before replacement; insertion failures roll back.
- Duplicate customer emails are warnings, not errors. Email is not unique in this dataset and is not treated as an identity key.
- An order total that differs from a subtotal calculated using today's supplied catalog prices is a warning. The original order total is preserved because historical prices or discounts may explain the difference.
- Multiple active promotions for one product are reported as a warning. No promotion is selected arbitrarily.
- Source CSV SHA-256 hashes and row counts are recorded in `dataset_metadata` for traceability.
- Personal customer fields and policy documents are not copied into this package and must not be committed to the public repository.

## Important limitation

The source files are a static challenge snapshot. Stock, promotions and order statuses are not live operational data. A successful load does not imply real-time synchronization with a store system.
