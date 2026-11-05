# M4 — Knowledge Base and RAG

M4 upgrades the policy-retrieval subsystem introduced in M3. It is an overlay for the existing M1 + M2 + M3 project: it adds the `app/knowledge` pipeline and replaces `app/services/policy_service.py` while preserving the public M3 `PolicyService` interface.

## What changed

- **PDF extraction:** `PolicyPdfExtractor` uses the PDF outline when available, recognizes section headings, ignores repeated headers/footers, and retains the physical page where each passage begins.
- **Section-aware chunking:** `PolicyChunker` keeps section boundaries intact, avoids mixing unrelated policy topics, and splits oversized passages using sentence/word boundaries.
- **Portuguese normalization:** `tokenizer.py` normalizes accents/case, removes stopwords, and expands a small auditable domain synonym dictionary.
- **Retrieval:** `BM25Retriever` ranks passages using BM25. Original query terms carry more weight than synonyms, and results are diversified by section.
- **Evidence threshold:** no positive lexical match means no evidence is returned. The assistant should ask for clarification or escalate instead of inventing an answer.
- **Conflict registry:** known policy ambiguities are isolated in an auditable registry, including warranty after day 30, freight at exactly R$ 500, conflicting contact details, and the documented installment interpretation.
- **Context formatting:** `format_policy_context` adds section/page references and explicitly frames retrieved text as reference data, not instructions.
- **Evaluation:** 24 golden questions measure section Recall@3 and MRR.

No new third-party dependency is required. The pipeline uses the existing PyMuPDF dependency and an in-repository BM25 implementation.

## Backward compatibility

The following M3 API remains supported:

```python
from app.services.policy_service import PolicyService

service = PolicyService("data/private/store_policies.pdf")
result = service.search("Como devolver uma compra feita online?", top_k=3)

for item in result.results:
    print(item.section, item.page, item.title, item.relevance_score)

conflicts = service.get_policy_conflicts("garantia depois de 45 dias")
requires_review = service.requires_human_review("frete para uma compra de R$ 500")
```

`PolicyService.extract_policy_chunks(pdf_path)`, `.load()`, `.search()`, `.get_policy_conflicts()` and `.requires_human_review()` remain available. `build_service_container()` does not need to change.

## Apply the ZIP

Extract `artefact_m4_knowledge_rag.zip` at the root of `emporio-ai-assistant`, preserving folder structure. The ZIP does not contain the restricted PDF, original CSVs, `.env`, `.venv`, or `.git`.

Required local source file:

```text
data/private/store_policies.pdf
```

The original manual must remain local and ignored by Git. The public repository should not contain the restricted PDF.

## Tests

Run unit tests (independent of the private manual):

```powershell
python -m pytest tests/unit -v
```

Run integration and evaluation tests (require the original CSVs and policy PDF in `data/private`):

```powershell
python -m pytest tests/integration tests/evaluations -v
```

Run the entire test suite:

```powershell
python -m pytest -q
```

Run the retrieval evaluation and print a JSON report:

```powershell
python -m app.knowledge
```

Or pass an explicit PDF path:

```powershell
python -m app.knowledge "data/private/store_policies.pdf"
```

The evaluation command exits successfully when Recall@3 is at least 0.90.

## Retrieval metrics

The supplied manual was evaluated with 24 manually authored queries mapped to expected section identifiers. In the build validation, the observed results were:

- Recall@3: **1.0000** (24/24 cases had at least one expected section in the first three results).
- Mean Reciprocal Rank (MRR): **0.9792**.

These are results on a small, document-specific evaluation set—not a claim of 100% general accuracy. Add new queries when policies or user language change. The normalized `relevance_score` is relative to the highest result for that query; it is not a calibrated probability or confidence percentage.

## Important operational notes

- The original PDF is version 2.1 (June 2025). The pipeline does not claim to know whether the store has since updated its policies.
- Physical PDF page numbers are returned with every evidence passage.
- The document's text is treated as untrusted reference content. It must never override system/developer instructions.
- The retriever only finds evidence; it does not decide legal questions or resolve contradictory store policy. The conflict registry signals cases requiring human review.
- The implementation does not send the PDF to Gemini. Only selected evidence passages will be passed to the model by the future orchestration layer.
