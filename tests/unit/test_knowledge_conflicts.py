from app.knowledge.conflict_registry import PolicyConflictRegistry


def test_warranty_more_than_30_days_requires_review():
    registry = PolicyConflictRegistry()
    assert registry.requires_human_review("Meu instrumento deu defeito depois de 45 dias") is True
    assert registry.requires_human_review("Meu instrumento deu defeito após 30 dias") is True


def test_basic_legal_warranty_question_is_not_automatically_escalated():
    registry = PolicyConflictRegistry()
    assert registry.requires_human_review("Qual é o prazo da garantia legal de 90 dias?") is False


def test_exact_500_freight_requires_review_but_above_500_does_not():
    registry = PolicyConflictRegistry()
    assert registry.requires_human_review("Qual o frete de uma compra de R$ 500?") is True
    assert registry.requires_human_review("Qual o frete de uma compra de R$ 550?") is False


def test_contact_and_installment_conflicts_are_documented():
    registry = PolicyConflictRegistry()
    assert any(item.key == "whatsapp_number" for item in registry.get_conflicts("Qual é o WhatsApp da loja?"))
    assert any(item.key == "email_spelling" for item in registry.get_conflicts("Qual o e-mail correto?"))
    installment = registry.get_conflicts("Qual o mínimo de parcela no crédito?")
    assert installment[0].status == "interpreted"
    assert registry.requires_human_review("Qual o mínimo de parcela no crédito?") is False
