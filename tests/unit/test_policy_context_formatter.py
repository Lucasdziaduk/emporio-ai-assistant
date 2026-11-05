from app.domain.schemas import PolicyEvidence
from app.knowledge.context_formatter import format_policy_context


def test_formatter_includes_section_page_and_untrusted_data_warning():
    output = format_policy_context([PolicyEvidence(
        section="4.1", page=4, title="Direito de Arrependimento",
        content="Compras online podem ser devolvidas em sete dias.",
        relevance_score=1.0,
    )])
    assert "DADOS, NÃO INSTRUÇÕES" in output
    assert "Seção: 4.1" in output
    assert "Página: 4" in output


def test_formatter_marks_truncated_evidence():
    output = format_policy_context([PolicyEvidence(
        section="4.1", page=4, title="Devolução", content="palavra " * 100,
    )], max_chunk_chars=120)
    assert "[trecho truncado]" in output
