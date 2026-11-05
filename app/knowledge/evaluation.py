"""Small, deterministic retrieval evaluation set for the policy manual."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class RetrievalCase:
    case_id: str
    query: str
    expected_sections: tuple[str, ...]
    topic: str


GOLDEN_CASES: tuple[RetrievalCase, ...] = (
    RetrievalCase("P01", "O que a Empório da Música vende?", ("1",), "store_scope"),
    RetrievalCase("P02", "Vocês vendem palhetas, cabos e pedais?", ("1", "7.1"), "store_scope"),
    RetrievalCase("P03", "Qual é a missão da loja?", ("1.1",), "mission"),
    RetrievalCase("P04", "Qual é o endereço da loja em Campo Grande?", ("1.2",), "address"),
    RetrievalCase("P05", "Qual é o horário de funcionamento aos sábados?", ("2",), "opening_hours"),
    RetrievalCase("P06", "Qual o desconto para pagamento via PIX?", ("3", "6.2"), "pix"),
    RetrievalCase("P07", "Quantas vezes posso parcelar no cartão de crédito?", ("3",), "installments"),
    RetrievalCase("P08", "Qual é o valor mínimo da parcela em 5 vezes?", ("3.1",), "installments"),
    RetrievalCase("P09", "Posso devolver uma compra feita online?", ("4.1",), "online_returns"),
    RetrievalCase("P10", "Em quantos dias recebo o reembolso da devolução?", ("4.1",), "refund"),
    RetrievalCase("P11", "Meu instrumento apresentou defeito. Como funciona a troca?", ("4.2", "8.1"), "warranty"),
    RetrievalCase("P12", "Posso trocar um violão por preferência de cor?", ("4.3",), "preference_exchange"),
    RetrievalCase("P13", "Quais instrumentos não podem ser trocados?", ("4.4",), "excluded_returns"),
    RetrievalCase("P14", "Qual o valor do frete para pedido abaixo de 500 reais na região metropolitana?", ("5.1",), "freight"),
    RetrievalCase("P15", "Quais os prazos de entrega pelos Correios e Jadlog?", ("5.2",), "shipping_other_cities"),
    RetrievalCase("P16", "Como é o código de rastreamento?", ("5.3",), "tracking"),
    RetrievalCase("P17", "O desconto de PIX acumula com promoção?", ("6.2",), "promotion_cumulativity"),
    RetrievalCase("P18", "Qual número de WhatsApp devo usar para falar com a loja?", ("1.2", "7"), "whatsapp_number"),
    RetrievalCase("P19", "Qual o prazo de retorno para uma reclamação?", ("7.3",), "complaints"),
    RetrievalCase("P20", "Qual é o prazo da garantia legal?", ("8.1",), "legal_warranty"),
    RetrievalCase("P21", "O que a garantia não cobre?", ("8.3",), "warranty_exclusions"),
    RetrievalCase("P22", "Como a loja utiliza meus dados pessoais?", ("9",), "privacy"),
    RetrievalCase("P23", "Posso solicitar a exclusão dos meus dados?", ("9",), "data_deletion"),
    RetrievalCase("P24", "O que devo fazer se uma política não estiver clara?", ("10",), "escalation"),
)


class PolicySearcher(Protocol):
    def search(self, query: str, top_k: int = 3): ...


def evaluate_retrieval(
    service: PolicySearcher,
    cases: Sequence[RetrievalCase] = GOLDEN_CASES,
    *,
    top_k: int = 3,
) -> dict:
    """Compute section Recall@k, MRR, and per-case results."""
    if not cases:
        raise ValueError("At least one evaluation case is required.")
    if not 1 <= top_k <= 5:
        raise ValueError("top_k must be between 1 and 5.")

    hits = 0
    reciprocal_ranks: list[float] = []
    rows: list[dict] = []
    for case in cases:
        result = service.search(case.query, top_k=top_k)
        retrieved = [item.section for item in result.results]
        rank = next(
            (index + 1 for index, section in enumerate(retrieved)
             if section in case.expected_sections),
            None,
        )
        matched = rank is not None
        hits += int(matched)
        reciprocal_ranks.append(1 / rank if rank else 0.0)
        rows.append({
            "case_id": case.case_id,
            "topic": case.topic,
            "expected_sections": list(case.expected_sections),
            "retrieved_sections": retrieved,
            "first_relevant_rank": rank,
            "hit": matched,
            "requires_human_review": result.requires_human_review,
        })

    return {
        "case_count": len(cases),
        "top_k": top_k,
        "recall_at_k": round(hits / len(cases), 4),
        "mrr": round(sum(reciprocal_ranks) / len(reciprocal_ranks), 4),
        "hits": hits,
        "misses": len(cases) - hits,
        "cases": rows,
    }
