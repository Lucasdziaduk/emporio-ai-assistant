# M3 — Business Services

This package adds the business-service layer on top of the existing M1 domain models and M2 SQLite/data layer. It is an overlay: it does not redistribute source CSVs, customer data, or the restricted policy PDF, and it does not replace M1/M2 modules.

## Included modules

- `app/services/money.py` — safe conversion between BRL and integer cents, plus Brazilian currency formatting.
- `app/services/catalog_service.py` — accent-insensitive product search, category/price/availability filters, sorting, and product details.
- `app/services/promotion_service.py` — active-promotion lookup and deterministic promotional-price calculation. Multiple active promotions for one product raise a policy conflict rather than choosing one.
- `app/services/payment_service.py` — PIX discount, promotion non-cumulativity, credit installments, minimum installment checks, and exact cent distribution.
- `app/services/identity_service.py` — local phone verification, per-session attempt limiting, and short-lived order/session-scoped authorization grants.
- `app/services/order_service.py` — order-status lookup requiring a valid authorization grant; returns only order items and static-dataset metadata.
- `app/services/policy_service.py` — local PDF text extraction, section-aware evidence chunks, lightweight BM25 retrieval, and known-policy-conflict detection.
- `app/services/store_service.py` — structured store address, hours, contact, payment methods and commercial scope.
- `app/services/container.py` — composition root wiring the repositories and services over one SQLite connection.
- `app/services/exceptions.py` — service-specific `ProductUnavailableError`, extending the existing application error base.

## Apply this package

Extract the ZIP into the **root** of the existing `emporio-ai-assistant` repository. The archive contains only M3 additions/overlays and M3 documentation/tests; it does not include `.venv`, `.git`, original CSVs, or the policy PDF.

The M3 implementation expects the existing M1 modules (`app/domain/enums.py`, `models.py`, `schemas.py`, `errors.py`) and M2 modules (`app/data/database.py`, `loader.py`, `repositories.py`) to remain in place.

## Run unit tests

From the project root, with `.venv` active:

```powershell
python -m pytest tests/unit -v
```

## Run integration tests with the original challenge files

The integration tests automatically use local files from:

```text
data/private/source/
    products.csv
    categories.csv
    promotions.csv
    customers.csv
    orders.csv
    order_items.csv

data/private/store_policies.pdf
```

The six CSVs are required for the dataset integration tests. The policy PDF test is skipped if the PDF is absent. These files must remain local and ignored by Git.

Run:

```powershell
python -m pytest tests/integration -v
```

When the original files are not present, the integration module is skipped with an explanatory reason; the unit tests remain runnable using synthetic data.

## Example: initialize the services

```python
from app.config import settings
from app.data import create_connection, load_dataset
from app.services import build_service_container

connection = create_connection(":memory:")
load_dataset(settings.private_data_dir / "source", connection)

services = build_service_container(
    connection,
    policy_pdf_path=settings.policy_pdf_path,
    auth_ttl_minutes=settings.order_auth_ttl_minutes,
    max_auth_attempts=3,
)
```

Use `services.catalog`, `services.promotions`, `services.payments`, `services.orders`, `services.identity`, `services.policies`, and `services.store_information` from the application layer. Close the SQLite connection when the application shuts down.

## Example: search products

```python
from app.domain.schemas import SearchProductsInput

result = services.catalog.search_products(
    SearchProductsInput(
        category="Violões",
        max_price_brl="1000.00",
        availability="available",
        sort_by="price_asc",
        limit=10,
    )
)
```

The service returns `ProductSearchData` with total matches, returned count, truncation flag and typed product summaries.

## Example: purchase conditions

```python
from app.domain.schemas import GetPurchaseConditionsInput

result = services.payments.get_purchase_conditions(
    GetPurchaseConditionsInput(product_id=95, payment_method="pix")
)
```

For the supplied Takamine GD20 record (product 95), the list price is R$ 2,199.00 and the non-promotional PIX result is R$ 2,089.05. A product with an active promotion does not receive an additional 5% PIX discount.

## Example: verify and inspect an order

Phone verification must be performed locally. Do not send the phone number to the LLM provider, put it in model history, or log it.

```python
grant = services.identity.verify_order_access(
    order_id=1,
    phone="(67) 98432-1098",  # local-only verification input
    session_id="conversation-session-id",
)

order = services.orders.get_order_status(
    order_id=1,
    authorization=grant,
    session_id="conversation-session-id",
)
```

The grant is restricted to one order and one session, expires after the configured time, and is invalid in another session. Three failed attempts lock verification for that session instance. In production, use an authenticated channel or stronger verification than a phone-number match.

## Example: retrieve policy evidence

```python
result = services.policies.search(
    "Qual o prazo para devolver uma compra online?",
    top_k=3,
)
```

The policy PDF is parsed locally on first search. The service returns only selected evidence chunks with section and page metadata. It does not transmit the PDF to Gemini. The BM25 scoring implementation is local and dependency-free; there is no hosted vector database.

## Important behavior and limitations

- All CSV values are a static snapshot, not live inventory, payment, or shipping data.
- Catalog availability is derived from product status and stock quantity.
- Money is represented internally as integer cents; input BRL values are converted using `Decimal`.
- Promotions are taken from `is_active`; the CSV has no promotion start/end dates.
- No active-promotion conflict is resolved arbitrarily.
- The manual's detailed installment table (section 3.1) is used for calculations; the general minimum stated in section 3 is documented as a policy inconsistency.
- Warranty cases after 30 days, freight for exactly R$ 500, and inconsistent contact details are flagged for human review.
- The service layer is deterministic and does not call an LLM. Function Calling and orchestration are a later integration step.
- No service creates, updates, cancels, or refunds orders.

## Test coverage

The M3 suite includes unit tests with synthetic repositories and integration tests against the supplied local challenge data. The latter check the 12 available violões within the R$ 1,000 filter, the Takamine PIX calculation, active-promotion non-cumulativity, authorized order lookup, PDF section retrieval, and store information.
