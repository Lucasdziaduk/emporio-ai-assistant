# M3 validation report

Validation performed in an isolated project assembled from the M2 package, the M1 domain contracts described in the project specification, and the original challenge data in a local test-only directory.

## Results

```text
57 passed
```

Additional checks:

```text
python -m compileall -q app/services tests/unit tests/integration
```

Compilation completed successfully.

## Test breakdown

- 13 existing M2 tests: database constraints, CSV parsing/loading, atomic reload, metadata/audit persistence and repository mapping.
- 37 M3 unit tests: money formatting, product search/details, promotion conflicts and calculations, PIX and installment rules, identity verification and lockout, order authorization and expiry, policy BM25 retrieval/conflict detection, and structured store information.
- 7 M3 integration tests using the original challenge files: 12-product violão filter, Takamine GD20 PIX result, promotion/PIX non-cumulativity, active promotion details, verified order lookup, real policy PDF extraction/search and structured store information.

## Real-data checks

- 191 rows loaded across the six CSV tables.
- `category=Violões`, `max_price_brl=1000`, `availability=available` returns 12 matches (10 in the requested page size).
- Product 95 (Takamine GD20) returns R$ 2,089.05 for PIX from a R$ 2,199.00 list price.
- Product 127 returns its 10% active promotional price of R$ 323.10; the 5% PIX discount is not stacked.
- Policy manual extraction produced section-aware chunks and retrieval for online right of regret selected section 4.1.
- Order 1 identity check succeeded using the matching local phone and returned static-snapshot metadata; phone values were not included in the returned order object.

## Scope of the result

This is a code/test validation against the supplied static dataset, not a claim of integration with live store systems, a carrier, WhatsApp, CRM or payment gateway. The private source files were used only in the isolated validation environment and are not included in the M3 ZIP.
