"""Integration and evaluation checks against the local restricted policy PDF."""

from pathlib import Path

import pytest

from app.knowledge.evaluation import GOLDEN_CASES, evaluate_retrieval
from app.services.policy_service import PolicyService

ROOT = Path(__file__).resolve().parents[2]
POLICY_PDF = ROOT / "data" / "private" / "store_policies.pdf"
pytestmark = pytest.mark.skipif(
    not POLICY_PDF.is_file(),
    reason="Original policy PDF is not present in data/private.",
)


def test_real_policy_pdf_extracts_required_sections_and_page_citations():
    service = PolicyService(POLICY_PDF)
    sections = {item.section for item in service.chunks}
    assert {"1", "1.1", "1.2", "2", "3", "3.1", "4.1", "4.2", "5.1", "5.2", "5.3", "6.1", "6.2", "7.1", "7.2", "7.3", "8.1", "8.2", "8.3", "9", "10"}.issubset(sections)

    shipping = service.search("Quais são os prazos de entrega para outras cidades?")
    assert shipping.results[0].section == "5.2"
    assert shipping.results[0].page == 5


def test_real_policy_retrieval_golden_set_reaches_target():
    service = PolicyService(POLICY_PDF)
    report = evaluate_retrieval(service, GOLDEN_CASES, top_k=3)
    assert report["case_count"] == 24
    assert report["recall_at_k"] >= 0.90
    assert report["mrr"] >= 0.85


def test_real_policy_flags_ambiguous_contact_and_commercial_cases():
    service = PolicyService(POLICY_PDF)
    assert service.search("Qual é o WhatsApp correto da loja?").requires_human_review
    assert service.search("Meu instrumento apresentou defeito depois de 45 dias?").requires_human_review
    assert service.search("Qual é o frete para uma compra de R$ 500?").requires_human_review
