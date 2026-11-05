from app.domain.schemas import PolicyEvidence
from app.knowledge.retriever import BM25Retriever


def test_retriever_ranks_exact_customer_question_first():
    documents = [
        PolicyEvidence(section="4.1", page=4, title="Direito de Arrependimento", content="Compras online podem ser devolvidas em até sete dias corridos após recebimento. Reembolso em até dez dias úteis."),
        PolicyEvidence(section="5.1", page=4, title="Frete", content="Frete grátis para pedidos acima de R$ 500,00."),
        PolicyEvidence(section="8.3", page=7, title="O que Não Cobre a Garantia", content="Desgaste natural, mau uso, quedas e modificações não autorizadas não são cobertos."),
    ]
    retriever = BM25Retriever(documents)
    results = retriever.retrieve("Como devolver uma compra feita online?", top_k=2)
    assert results[0].section == "4.1"
    assert results[0].relevance_score == 1.0


def test_retriever_returns_no_evidence_for_unrelated_query():
    documents = [PolicyEvidence(
        section="2", page=2, title="Horário de funcionamento",
        content="A loja funciona de segunda a sexta-feira.",
    )]
    assert BM25Retriever(documents).retrieve("Qual é o número de série da guitarra?") == []


def test_retriever_rejects_invalid_top_k():
    retriever = BM25Retriever([PolicyEvidence(section="2", page=2, title="Horários", content="Funcionamento da loja.")])
    try:
        retriever.retrieve("horário da loja", top_k=0)
    except ValueError as exc:
        assert "top_k" in str(exc)
    else:
        raise AssertionError("Invalid top_k should be rejected.")


def test_retriever_limits_repeated_section_results():
    documents = [
        PolicyEvidence(section="4.1", page=4, title="Devolução", content=f"Regra de devolução online e reembolso {i} dias.")
        for i in range(4)
    ] + [PolicyEvidence(section="4.2", page=4, title="Defeito", content="Troca por defeito de fabricação.")]
    results = BM25Retriever(documents, max_per_section=1).retrieve("devolução online reembolso", top_k=3)
    assert len([item for item in results if item.section == "4.1"]) <= 1
