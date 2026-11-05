"""Auditable registry of policy ambiguities and review triggers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from app.knowledge.tokenizer import normalize_text, tokenize


@dataclass(frozen=True)
class PolicyConflict:
    key: str
    sections: tuple[str, ...]
    status: str
    description: str
    action: str


POLICY_CONFLICTS: dict[str, PolicyConflict] = {
    "warranty_after_30_days": PolicyConflict(
        key="warranty_after_30_days",
        sections=("4.2", "8.1"),
        status="unresolved",
        description=(
            "Section 4.2 directs customers to the manufacturer after 30 days, "
            "while section 8.1 states a 90-day legal warranty. Do not deny coverage; "
            "cases after day 30 require human review."
        ),
        action="human_review",
    ),
    "freight_exactly_500": PolicyConflict(
        key="freight_exactly_500",
        sections=("5.1",),
        status="unresolved",
        description=(
            "Section 5.1 gives free freight above R$ 500 and R$ 35 below R$ 500, "
            "but does not specify a purchase of exactly R$ 500."
        ),
        action="human_review",
    ),
    "email_spelling": PolicyConflict(
        key="email_spelling",
        sections=("cover", "1.2"),
        status="unresolved",
        description=(
            "The cover and section 1.2 show different spellings of the email domain. "
            "Do not publish an email address until staff confirms it."
        ),
        action="human_review",
    ),
    "whatsapp_number": PolicyConflict(
        key="whatsapp_number",
        sections=("cover", "1.2", "7"),
        status="unresolved",
        description=(
            "The cover and section 1.2 list (67) 3341-4444 as phone/WhatsApp, "
            "while section 7 identifies (67) 3321-4500 as the main WhatsApp channel. "
            "Do not designate a single primary WhatsApp number without confirmation."
        ),
        action="human_review",
    ),
    "installment_minimums": PolicyConflict(
        key="installment_minimums",
        sections=("3", "3.1"),
        status="interpreted",
        description=(
            "Section 3 gives a general R$ 100 minimum installment, while section 3.1 "
            "specifies R$ 50 for 1-3x, R$ 80 for 4-6x and R$ 100 for 7-12x. "
            "The implementation adopts the detailed section 3.1 rule."
        ),
        action="documented_interpretation",
    ),
}


class PolicyConflictRegistry:
    """Match policy topics against documented ambiguities."""

    def get_conflicts(self, topic: str) -> list[PolicyConflict]:
        normalized = normalize_text(topic).strip()
        tokens = set(tokenize(topic))
        if normalized in POLICY_CONFLICTS:
            return [POLICY_CONFLICTS[normalized]]

        matches: list[PolicyConflict] = []
        warranty_related = bool(tokens.intersection({"garantia", "defeito", "troca", "fabricante"}))
        # A broad request covering both exchange and return can surface section
        # 4.2 (manufacturer after 30 days) alongside section 8.1 (90-day legal
        # warranty). Flag that combined topic before the LLM summarizes only
        # one side of the unresolved policy conflict. A precise preference
        # exchange remains answerable from section 4.3.
        broad_exchange_and_return = (
            "troca" in tokens
            and "devolucao" in tokens
            and "preferencia" not in tokens
        )
        if warranty_related and (
            self._mentions_after_30_days(normalized) or broad_exchange_and_return
        ):
            matches.append(POLICY_CONFLICTS["warranty_after_30_days"])
        if tokens.intersection({"frete", "entrega", "envio"}) and self._mentions_exact_500(normalized):
            matches.append(POLICY_CONFLICTS["freight_exactly_500"])
        if tokens.intersection({"email", "mail", "contato"}):
            matches.append(POLICY_CONFLICTS["email_spelling"])
        if tokens.intersection({"whatsapp", "telefone", "celular", "numero"}):
            matches.append(POLICY_CONFLICTS["whatsapp_number"])
        if tokens.intersection({"parcelamento", "parcela", "credito"}):
            matches.append(POLICY_CONFLICTS["installment_minimums"])
        return self._unique(matches)

    def requires_human_review(self, topic: str) -> bool:
        return any(item.action == "human_review" for item in self.get_conflicts(topic))

    @staticmethod
    def _mentions_after_30_days(normalized: str) -> bool:
        patterns = (
            r"\b(?:apos|depois de|passados?|faz|ha)\s+(?:os\s+)?(\d{2,3})\s+dias\b",
            r"\b(3[1-9]|[4-8]\d|90)\s+dias\s+(?:apos|depois)\b",
            r"\bentre\s+30\s+e\s+90\s+dias\b",
            r"\bmais\s+de\s+30\s+dias\b",
            r"\b31\s+dias\b",
        )
        for pattern in patterns:
            for match in re.finditer(pattern, normalized):
                number = next((group for group in match.groups() if group), None)
                if number is None or int(number) >= 30:
                    return True
        return False

    @staticmethod
    def _mentions_exact_500(normalized: str) -> bool:
        patterns = (
            r"r\$\s*500(?:[,.]00)?\b",
            r"\b500(?:[,.]00)?\s*(?:reais|real)\b",
            r"\bexatamente\s+500\b",
            r"\bcompra\s+(?:de\s+)?500\b",
        )
        return any(re.search(pattern, normalized) for pattern in patterns)

    @staticmethod
    def _unique(items: Iterable[PolicyConflict]) -> list[PolicyConflict]:
        output: list[PolicyConflict] = []
        seen: set[str] = set()
        for item in items:
            if item.key not in seen:
                output.append(item)
                seen.add(item.key)
        return output
