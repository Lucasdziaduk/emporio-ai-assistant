from app.domain.schemas import PolicyEvidence
from app.services.policy_service import PolicyService
from app.services.store_service import StoreInformationService


def test_policy_search_retrieves_relevant_return_policy():
    chunks = [
        PolicyEvidence(
            section="4.1", page=4, title="Direito de Arrependimento",
            content="Compras online podem ser devolvidas em até sete dias corridos após o recebimento. O reembolso ocorre na forma original em até dez dias úteis."
        ),
        PolicyEvidence(
            section="5.1", page=5, title="Entregas na Região Metropolitana",
            content="Frete grátis para pedidos acima de quinhentos reais e taxa fixa abaixo desse valor."
        ),
    ]
    service = PolicyService(chunks=chunks)
    result = service.search("Como devolver uma compra online?", top_k=2)
    assert result.results
    assert result.results[0].section == "4.1"
    assert result.results[0].relevance_score == 1.0


def test_policy_search_flags_exact_freight_threshold_for_review():
    service = PolicyService(chunks=[
        PolicyEvidence(section="5.1", page=5, title="Frete", content="Frete grátis acima de R$ 500 e R$ 35 abaixo de R$ 500.")
    ])
    result = service.search("Qual é o frete para uma compra de R$ 500?")
    assert result.requires_human_review is True


def test_policy_search_flags_warranty_after_30_days():
    service = PolicyService(chunks=[
        PolicyEvidence(section="4.2", page=4, title="Defeitos", content="Após 30 dias, o cliente deve acionar o fabricante. A garantia legal consta da seção 8.1.")
    ])
    result = service.search("Meu instrumento apresentou defeito depois de 30 dias, ainda tenho garantia?")
    assert result.requires_human_review is True


def test_policy_search_returns_no_evidence_for_unmatched_query():
    service = PolicyService(chunks=[
        PolicyEvidence(section="2", page=2, title="Horários", content="A loja abre de segunda a sexta das nove às dezoito horas.")
    ])
    result = service.search("Qual é o código de fabricação da guitarra?")
    assert result.results == []


def test_policy_conflict_registry_marks_installments_as_interpreted():
    service = PolicyService(chunks=[
        PolicyEvidence(section="3", page=3, title="Pagamento", content="Cartão de crédito até doze vezes.")
    ])
    conflicts = service.get_policy_conflicts("parcelamento")
    assert len(conflicts) == 1
    assert conflicts[0].status == "interpreted"
    assert conflicts[0].action == "documented_interpretation"


def test_store_information_does_not_publish_conflicting_email():
    result = StoreInformationService().get_information("contact")
    assert result.content["phone_number_listed_on_cover_and_section_1_2"] == "(67) 3341-4444"
    assert result.content["whatsapp_number_listed_in_section_7"] == "(67) 3321-4500"
    assert result.content["primary_whatsapp"] is None
    assert result.content["phone_requires_human_confirmation"] is True
    assert result.content["email"] is None
    assert result.content["email_requires_human_confirmation"] is True


def test_store_scope_does_not_invent_partner_stores():
    result = StoreInformationService().get_information("store_scope")
    assert "palhetas" in result.content["examples_out_of_scope"]
    assert "Não há lojas parceiras" in result.content["partner_recommendations"]


def test_policy_conflict_registry_flags_ambiguous_whatsapp_number():
    service = PolicyService(chunks=[
        PolicyEvidence(section="7", page=6, title="WhatsApp", content="WhatsApp principal da loja.")
    ])
    conflicts = service.get_policy_conflicts("qual é o telefone WhatsApp da loja")
    assert any(item.key == "whatsapp_number" for item in conflicts)
