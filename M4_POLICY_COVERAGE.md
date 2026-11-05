# M4 — Policy coverage and escalation register

This file records how the knowledge layer indexes the supplied internal manual. It is not a replacement for the manual and does not constitute legal advice or a store-approved policy amendment.

## Indexed sections

The extractor recognizes the cover and the following numbered sections/subsections when present in the PDF outline:

| Section | Topic | PDF page(s) represented in retrieved chunks |
|---|---|---:|
| 1 | Sobre a Empório da Música | 2 |
| 1.1 | Missão | 2 |
| 1.2 | Dados da Empresa | 2 |
| 2 | Horário de Funcionamento | 2 |
| 3 | Formas de Pagamento | 3 |
| 3.1 | Regras de Parcelamento | 3 |
| 4.1 | Direito de Arrependimento | 4 |
| 4.2 | Trocas por Defeito | 4 |
| 4.3 | Trocas por Preferência | 4 |
| 4.4 | Itens Não Elegíveis para Troca | 4 |
| 5.1 | Entregas na Região Metropolitana | 4 |
| 5.2 | Entregas para Outras Cidades | 5 |
| 5.3 | Código de Rastreamento | 5 |
| 6.1 | Tipos de Promoção | 6 |
| 6.2 | Regras de Promoções | 6 |
| 7 | Atendimento via WhatsApp | 6 |
| 7.1 | Diretrizes de Atendimento | 6 |
| 7.2 | Fluxo de Atendimento Padrão | 6–7 |
| 7.3 | Situações Especiais | 7 |
| 8.1 | Garantia Legal | 7 |
| 8.2 | Garantia do Fabricante | 7 |
| 8.3 | O que Não Cobre a Garantia | 7 |
| 9 | Privacidade e Proteção de Dados | 7–8 |
| 10 | Disposições Finais | 8 |

Some parent headings (for example, section 8) are structural headings without body text; the retriever returns the relevant child sections rather than fabricating a parent passage.

## Conflict and review rules

| Key | Source sections | Status | Automated behavior |
|---|---|---|---|
| `warranty_after_30_days` | 4.2, 8.1 | Unresolved | Questions indicating a defect/warranty after 30 days require human review. The agent must not deny the stated 90-day legal warranty. |
| `freight_exactly_500` | 5.1 | Unresolved | A shipping question for an order of exactly R$ 500 requires human review. |
| `email_spelling` | Cover, 1.2 | Unresolved | An email-contact question requires human confirmation; do not publish one spelling as verified. |
| `whatsapp_number` | Cover, 1.2, 7 | Unresolved | Phone/WhatsApp contact questions require confirmation of the primary channel. |
| `installment_minimums` | 3, 3.1 | Interpreted | The implementation adopts the detailed subsection 3.1 thresholds (R$ 50 for 1–3x; R$ 80 for 4–6x; R$ 100 for 7–12x), documenting that section 3 has a broader R$ 100 statement. Not automatically escalated in this prototype. |

## Scope of evidence

- The PDF is an internal manual marked for restricted staff use. Keep the original file in `data/private/` and out of the public Git repository.
- Search results include the PDF's physical page number and section identifier.
- A passage being retrieved does not mean the request is fully resolved; the agent still has to apply the correct rule and check the conflict registry.
- The PDF states that the store works exclusively with musical instruments. The agent must not invent accessory inventory or partner-store recommendations.
- The policy manual is dated June 2025. The retrieval system cannot verify later policy updates.
