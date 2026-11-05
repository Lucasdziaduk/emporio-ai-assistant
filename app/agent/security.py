"""Privacy helpers for messages handled before they reach the LLM."""

from __future__ import annotations

import re


# Brazilian domestic numbers are normally 10 or 11 digits including area code.
# This deliberately errs on the side of redaction rather than retaining a phone.
_PHONE_LIKE = re.compile(r"(?<!\d)(?:\+?55[\s().-]*)?\(?\d{2}\)?[\s().-]*9?\d{4}[\s.-]?\d{4}(?!\d)")
_PHONE_CONTEXT = re.compile(
    r"(?P<prefix>\b(?:telefone|celular|whatsapp)\b\D{0,16})(?P<number>\+?\d[\d\s().-]{6,}\d)",
    re.IGNORECASE,
)


def contains_phone_like_value(text: str) -> bool:
    value = text or ""
    if _PHONE_LIKE.search(value):
        return True
    match = _PHONE_CONTEXT.search(value)
    if match:
        digits = "".join(character for character in match.group("number") if character.isdigit())
        return 8 <= len(digits) <= 15
    return False


def redact_phone_like_values(text: str) -> str:
    value = _PHONE_LIKE.sub("[telefone removido por privacidade]", text or "")

    def replace_context_match(match: re.Match[str]) -> str:
        digits = "".join(character for character in match.group("number") if character.isdigit())
        if 8 <= len(digits) <= 15:
            return match.group("prefix") + "[telefone removido por privacidade]"
        return match.group(0)

    return _PHONE_CONTEXT.sub(replace_context_match, value)


def normalize_phone_input(text: str) -> str:
    return "".join(character for character in (text or "") if character.isdigit())


def looks_like_cancel(text: str) -> bool:
    normalized = " ".join((text or "").casefold().strip().split())
    return normalized in {"cancelar", "cancela", "desistir", "não quero", "nao quero", "voltar"}
