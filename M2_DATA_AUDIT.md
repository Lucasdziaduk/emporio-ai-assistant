# M2 source-data audit

Audit performed against the six CSV files contained in the supplied challenge ZIP. The original files are not redistributed in this implementation package.

## Source inventory

| File | Records |
|---|---:|
| `categories.csv` | 9 |
| `products.csv` | 65 |
| `promotions.csv` | 25 |
| `customers.csv` | 50 |
| `orders.csv` | 20 |
| `order_items.csv` | 22 |
| **Total** | **191** |

The orders span **2025-10-15 through 2026-03-22**. Four promotion records have `is_active = 1`.

## Observations recorded by the loader

1. Customer records 11 and 43 share an email address. Email is not treated as a unique identifier; both records are preserved.
2. Order 3 has a recorded total of R$ 3,450.00, while the sum using current catalog prices and the order-item quantities is R$ 3,498.00. The recorded order total is preserved; the difference is a warning, not a load failure.
3. Order 20 has a recorded total of R$ 1,400.00, while the sum using current catalog prices and the order-item quantities is R$ 1,488.00. The recorded order total is preserved; the difference is a warning, not a load failure.

These comparisons use current catalog prices because the CSV set does not contain historical unit prices per order item. Differences may represent historical prices, negotiated prices, or discounts; the source does not allow us to determine which explanation is correct.

## Validation results

- No duplicate primary keys were found.
- No duplicate `(order_id, product_id)` order-item keys were found.
- No invalid foreign-key relationships were found.
- Product status and order status values match the enums already defined in the project.
- Product `specs` values are valid JSON objects with string values.
- Blank tracking codes, delivery dates, and notes are treated as nullable fields.
- No customer email uniqueness constraint is imposed.

## Money conversion

`price_brl` and `total_brl` are decimal values expressed in Brazilian reais. The ingestion layer parses them with `Decimal` and converts them to integer cents. For example, `599.9` becomes `59990`, and `11499` becomes `1149900`. No binary floating-point arithmetic is used.

## Security and publication

The challenge CSVs include customer names, telephone numbers and email addresses, and the PDF policy document is marked as restricted/internal. Neither the source data nor the original policy PDF is included in this code package. Keep them in `data/private/`, which is ignored by Git. A sanitized public sample dataset must be prepared separately before the public repository is advertised as fully reproducible from its contents alone.
