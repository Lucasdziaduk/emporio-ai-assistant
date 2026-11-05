# M3 — Policy and business-rule decisions

This record documents implementation choices taken from the supplied Empório da Música policy manual (version 2.1, June 2025) and the static challenge CSV snapshot. It does not replace the manual or claim to resolve business decisions that require store approval.

| Topic | Source | Implementation decision | Escalation |
|---|---|---|---|
| Product availability | `products.csv`; manual section 7.3 | A product is saleable only when status is `active` and stock is greater than zero. | No automatic backorder or rain check. |
| Promotion validity | `promotions.csv`; manual section 6.2 | The dataset's `is_active` flag is the available source of truth; the file has no start/end dates. | Do not infer expiration dates. |
| Multiple active promotions | `promotions.csv`; manual section 6.2 | Do not select one arbitrarily; raise a policy conflict. | Human review. |
| PIX | Manual sections 3 and 6.2 | Apply 5% to list price only when there is no active promotion. | Do not stack PIX with a promotional price. |
| Installment minimums | Manual sections 3 and 3.1 | Implement the specific table in 3.1: R$ 50 for 1–3x, R$ 80 for 4–6x, R$ 100 for 7–12x, all without interest. | Documented interpretation; confirm with store before production. |
| Warranty after 30 days | Manual sections 4.2 and 8.1 | Do not deny the 90-day legal warranty. Section 4.2 directs the customer to the manufacturer after 30 days; section 8.1 states a 90-day legal warranty. | Cases after 30 days require human review. |
| Freight at exactly R$ 500 | Manual section 5.1 | The manual specifies free shipping above R$ 500 and R$ 35 below R$ 500, but does not define exactly R$ 500. | Human review. |
| Contact phone numbers | Cover, section 1.2 and section 7 | The manual lists (67) 3341-4444 on the cover and as phone/WhatsApp in section 1.2; section 7 calls (67) 3321-4500 the main WhatsApp channel. | Neither is designated as the primary WhatsApp number until confirmed. Both values are exposed with their source context only. |
| Email spelling | Cover and section 1.2 | The domain appears with and without an accent. | Do not publish an email address until confirmed. |
| Product scope | Manual sections 1 and 7.1 | Store sells musical instruments only, not accessories such as strings, picks, cables, cases, pedals or amplifiers. | Do not invent partner-store recommendations. |
| Complaints | Manual section 7.3 | The policy states 24 business hours for return contact. The prototype has no ticketing/CRM integration. | Never claim a complaint was registered or forwarded. |
| Order status and delivery | Static `orders.csv` | Present the saved status and tracking details as a snapshot, not a live carrier result. | Never claim current package location or a current ETA. |

## Static dataset facts checked during M3 integration

- 65 products, 9 categories, 25 promotions, 50 customers, 20 orders and 22 order items.
- 12 products match `category=Violões`, price at or below R$ 1,000, active status and positive stock.
- Product 95 (Takamine GD20 Dreadnought Natural) has list price R$ 2,199.00 and no active promotion; its PIX price is R$ 2,089.05.
- The four active promotions are for product IDs 127 (10%), 121 (20%), 90 (18%) and 94 (8%).
- Order data ranges from 2025-10-15 through 2026-03-22.

These are facts about the supplied snapshot only; they must not be described as live store data.
