"""Structured store information transcribed from the supplied policy manual."""

from app.domain.schemas import StoreInfoTopic, StoreInformationData


class StoreInformationService:
    """Provide stable institutional information with explicit caveats."""

    def get_information(self, topic: StoreInfoTopic) -> StoreInformationData:
        if topic == "address":
            content = {
                "legal_name": "Empório da Música Instrumentos Musicais Ltda.",
                "trade_name": "Empório da Música",
                "address": "Rua 14 de Maio, 3200 — Centro, Campo Grande - MS, 79202-333",
                "founded_year": 2008,
                "source_version": "Manual de Políticas v2.1 — junho de 2025",
            }
        elif topic == "opening_hours":
            content = {
                "monday_to_friday": "09:00 às 18:00",
                "saturday": "09:00 às 13:00",
                "sunday_and_holidays": "Fechado",
                "whatsapp_follows_store_hours": True,
                "note": "Horários especiais podem ser comunicados pela loja.",
            }
        elif topic == "contact":
            content = {
                "phone_number_listed_on_cover_and_section_1_2": "(67) 3341-4444",
                "whatsapp_number_listed_in_section_7": "(67) 3321-4500",
                "primary_whatsapp": None,
                "phone_requires_human_confirmation": True,
                "phone_note": (
                    "A capa e a seção 1.2 associam o primeiro número a telefone/WhatsApp, "
                    "mas a seção 7 identifica o segundo como WhatsApp principal. "
                    "Confirme com a equipe qual número deve ser divulgado como principal."
                ),
                "email": None,
                "email_requires_human_confirmation": True,
                "email_note": (
                    "O manual apresenta grafias diferentes para o domínio do e-mail. "
                    "Confirme o endereço com a equipe antes de compartilhá-lo."
                ),
            }
        elif topic == "payment_methods":
            content = {
                "pix": {"type": "à vista", "discount_percent": 5},
                "debit": {"type": "à vista", "discount_percent": 0},
                "credit": {
                    "max_installments": 12,
                    "interest": 0,
                    "minimums_by_range": [
                        {"installments": "1-3", "minimum_installment_cents": 5000},
                        {"installments": "4-6", "minimum_installment_cents": 8000},
                        {"installments": "7-12", "minimum_installment_cents": 10000},
                    ],
                },
                "boleto": {"type": "à vista", "compensation": "até 3 dias úteis"},
                "pix_promotion_rule": "O desconto PIX não é cumulativo com promoções.",
                "installment_rule_note": (
                    "O manual contém um mínimo geral de R$ 100,00 na seção 3 e "
                    "mínimos específicos na seção 3.1. O serviço adota a tabela detalhada 3.1."
                ),
            }
        else:  # store_scope
            content = {
                "scope": "A loja comercializa exclusivamente instrumentos musicais.",
                "examples_in_scope": [
                    "guitarras", "baixos", "violões", "baterias", "teclados",
                    "instrumentos de sopro", "cordas orquestrais", "ukuleles",
                ],
                "examples_out_of_scope": [
                    "cordas", "palhetas", "cabos", "cases", "pedais", "amplificadores",
                ],
                "partner_recommendations": "Não há lojas parceiras identificadas no material fornecido.",
            }

        return StoreInformationData(topic=topic, content=content)
