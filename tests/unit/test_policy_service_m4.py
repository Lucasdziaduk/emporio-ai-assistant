import pytest

from app.domain.schemas import PolicyEvidence
from app.services.policy_service import PolicyService


def test_policy_service_backward_compatible_with_m3_constructor():
    service = PolicyService(chunks=[PolicyEvidence(
        section="4.1", page=4, title="Direito de Arrependimento",
        content="Compras online podem ser devolvidas em até sete dias corridos.",
    )])
    result = service.search("Como devolver uma compra online?")
    assert result.results[0].section == "4.1"


def test_policy_service_flags_ambiguous_cases_without_pdf():
    service = PolicyService(chunks=[PolicyEvidence(
        section="5.1", page=4, title="Frete regional",
        content="Frete grátis para pedidos acima de R$ 500 e taxa abaixo desse valor.",
    )])
    assert service.search("Qual o frete para uma compra de R$ 500?").requires_human_review


def test_policy_service_returns_empty_evidence_when_nothing_matches():
    service = PolicyService(chunks=[PolicyEvidence(
        section="2", page=2, title="Horário de funcionamento",
        content="A loja funciona de segunda a sexta-feira.",
    )])
    assert service.search("Qual é o número de série da guitarra?").results == []


def test_policy_service_validates_query_and_top_k():
    service = PolicyService(chunks=[PolicyEvidence(
        section="2", page=2, title="Horário", content="Funcionamento da loja.",
    )])
    with pytest.raises(ValueError):
        service.search("oi")
    with pytest.raises(ValueError):
        service.search("horário da loja", top_k=0)


def test_policy_service_missing_pdf_raises_safe_source_error(tmp_path):
    from app.domain.errors import SourceUnavailableError
    service = PolicyService(tmp_path / "missing.pdf")
    with pytest.raises(SourceUnavailableError):
        service.search("Qual é o horário de funcionamento?")
