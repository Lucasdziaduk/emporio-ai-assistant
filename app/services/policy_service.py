"""Policy PDF extraction, BM25 retrieval, and conflict awareness.

The source document stays local. Only selected evidence chunks are returned
from this service; the PDF itself is never sent to an LLM provider.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from app.domain.errors import SourceUnavailableError
from app.domain.schemas import PolicyEvidence, PolicySearchData


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
            "while section 8.1 states a 90-day legal warranty. The assistant must "
            "not deny coverage; cases after day 30 require human review."
        ),
        action="human_review",
    ),
    "freight_exactly_500": PolicyConflict(
        key="freight_exactly_500",
        sections=("5.1",),
        status="unresolved",
        description=(
            "Section 5.1 defines free freight for orders above R$ 500 and a R$ 35 "
            "fee below R$ 500, but does not define an order of exactly R$ 500."
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
            "The cover and section 1.2 associate (67) 3341-4444 with phone/WhatsApp, "
            "while section 7 identifies (67) 3321-4500 as the main WhatsApp channel. "
            "Do not identify a single primary WhatsApp number without confirmation."
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
            "This implementation adopts the detailed section 3.1 rule."
        ),
        action="documented_interpretation",
    ),
}


_STOPWORDS = {
    "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do", "dos",
    "e", "em", "essa", "esse", "esta", "este", "eu", "me", "meu", "minha",
    "na", "nas", "no", "nos", "o", "os", "ou", "para", "por", "qual", "que",
    "se", "sem", "sobre", "tem", "tenho", "um", "uma", "vocês", "voces",
}

_SYNONYMS: dict[str, tuple[str, ...]] = {
    "devolver": ("devolucao", "arrependimento", "reembolso", "estorno", "compra", "online"),
    "devolucao": ("arrependimento", "reembolso", "estorno", "prazo"),
    "arrependi": ("arrependimento", "devolucao", "reembolso", "online"),
    "arrependimento": ("devolucao", "reembolso", "estorno", "online"),
    "dinheiro": ("reembolso", "estorno", "pagamento"),
    "estorno": ("reembolso", "devolucao", "pagamento"),
    "quebrou": ("defeito", "garantia", "fabricacao", "troca"),
    "defeito": ("garantia", "fabricacao", "troca", "reparo"),
    "garantia": ("defeito", "fabricante", "legal", "noventa", "dias"),
    "entrega": ("frete", "transportadora", "prazo", "rastreamento"),
    "rastrear": ("rastreamento", "codigo", "despachado", "entrega"),
    "parcelar": ("parcelamento", "credito", "parcela", "juros"),
    "parcelamento": ("parcelas", "credito", "juros", "minima"),
    "pix": ("desconto", "cumulativo", "promocao"),
    "horario": ("funcionamento", "sabado", "domingo", "feriados"),
}


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def _tokenize(value: str) -> list[str]:
    normalized = _normalize(value)
    tokens = re.findall(r"[a-z0-9]+", normalized)
    return [token for token in tokens if token not in _STOPWORDS and len(token) > 1]


class _BM25Index:
    """Small dependency-free BM25 index suitable for the supplied short manual."""

    def __init__(self, documents: Sequence[str], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.documents = [_tokenize(document) for document in documents]
        self.k1 = k1
        self.b = b
        self.doc_count = len(self.documents)
        self.avgdl = (
            sum(len(document) for document in self.documents) / self.doc_count
            if self.doc_count else 0.0
        )
        self.term_frequencies: list[dict[str, int]] = []
        document_frequency: dict[str, int] = {}
        for document in self.documents:
            frequencies: dict[str, int] = {}
            for token in document:
                frequencies[token] = frequencies.get(token, 0) + 1
            self.term_frequencies.append(frequencies)
            for token in frequencies:
                document_frequency[token] = document_frequency.get(token, 0) + 1
        self.idf = {
            token: math.log(1 + (self.doc_count - freq + 0.5) / (freq + 0.5))
            for token, freq in document_frequency.items()
        }

    def scores(self, query_tokens: Sequence[str]) -> list[float]:
        scores: list[float] = []
        for frequencies, document in zip(self.term_frequencies, self.documents):
            score = 0.0
            doc_len = len(document)
            for token in query_tokens:
                frequency = frequencies.get(token, 0)
                if frequency == 0:
                    continue
                idf = self.idf.get(token, 0.0)
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * (doc_len / self.avgdl if self.avgdl else 0)
                )
                score += idf * (frequency * (self.k1 + 1)) / denominator
            scores.append(score)
        return scores


class PolicyService:
    """Extract policy sections from the local PDF and retrieve relevant evidence."""

    HEADING_PATTERN = re.compile(r"^\s*(\d+\.\d+|\d+\.)\s+(.+?)\s*$")

    def __init__(
        self,
        policy_pdf_path: str | Path | None = None,
        *,
        chunks: Sequence[PolicyEvidence] | None = None,
    ) -> None:
        self.policy_pdf_path = Path(policy_pdf_path) if policy_pdf_path else None
        self._chunks: list[PolicyEvidence] = list(chunks or [])
        self._index: _BM25Index | None = None
        if self._chunks:
            self._build_index()

    @classmethod
    def extract_policy_chunks(cls, pdf_path: str | Path) -> list[PolicyEvidence]:
        """Extract sections from the policy manual while preserving page numbers."""
        path = Path(pdf_path)
        if not path.is_file():
            raise SourceUnavailableError()
        try:
            import fitz
            document = fitz.open(path)
        except Exception as exc:
            raise SourceUnavailableError() from exc

        chunks: list[PolicyEvidence] = []
        current_section = "cover"
        current_title = "Capa e dados gerais"
        current_page = 1
        current_lines: list[str] = []

        def flush() -> None:
            content = "\n".join(line.strip() for line in current_lines if line.strip()).strip()
            if content:
                chunks.append(PolicyEvidence(
                    section=current_section,
                    page=current_page,
                    title=current_title,
                    content=content,
                ))

        try:
            for page_index, page in enumerate(document, start=1):
                text = page.get_text("text")
                for raw_line in text.splitlines():
                    line = raw_line.strip()
                    if not line:
                        continue
                    if line.startswith("Empório da Música Manual de Políticas"):
                        continue
                    if re.fullmatch(r"Página\s+\d+", line, flags=re.IGNORECASE):
                        continue

                    heading = cls.HEADING_PATTERN.match(line)
                    if heading:
                        flush()
                        current_section = heading.group(1).rstrip(".")
                        current_title = heading.group(2).strip()
                        current_page = page_index
                        current_lines = []
                    else:
                        if not current_lines and current_section != "cover" and current_page != page_index:
                            # A section can continue on the next page.
                            current_page = page_index
                        current_lines.append(line)
            flush()
        finally:
            document.close()

        if not chunks:
            raise SourceUnavailableError()
        return chunks

    def load(self) -> None:
        if self._chunks:
            self._build_index()
            return
        if self.policy_pdf_path is None:
            raise SourceUnavailableError()
        self._chunks = self.extract_policy_chunks(self.policy_pdf_path)
        self._build_index()

    def _build_index(self) -> None:
        self._index = _BM25Index([
            f"{chunk.section} {chunk.title} {chunk.content}"
            for chunk in self._chunks
        ])

    @staticmethod
    def _expand_query(query: str) -> list[str]:
        tokens = _tokenize(query)
        expanded = list(tokens)
        for token in tokens:
            expanded.extend(_SYNONYMS.get(token, ()))
        # Preserve order while removing duplicates.
        return list(dict.fromkeys(expanded))

    @staticmethod
    def _requires_review(query: str) -> bool:
        normalized = _normalize(query)
        tokens = set(_tokenize(query))

        warranty_related = bool(tokens.intersection({"garantia", "defeito", "troca", "fabricante"}))
        mentions_after_30 = bool(re.search(
            r"(apos|depois de|passados?)\s+(os\s+)?30\s+dias|31\s+dias|mais de 30 dias|entre 30 e 90 dias",
            normalized,
        ))
        if warranty_related and mentions_after_30:
            return True

        freight_related = bool(tokens.intersection({"frete", "entrega", "frete"}))
        exact_500 = bool(re.search(r"\b500(?:[,.]00)?\b", normalized))
        if freight_related and exact_500:
            return True

        if "email" in tokens or "e-mail" in normalized:
            return True

        return False

    def search(self, query: str, top_k: int = 3) -> PolicySearchData:
        """Return the top evidence passages; empty results mean no evidence found."""
        if not query or len(query.strip()) < 3:
            raise ValueError("Policy query must contain at least three characters.")
        if not 1 <= top_k <= 5:
            raise ValueError("top_k must be between 1 and 5.")
        if self._index is None:
            self.load()

        assert self._index is not None
        query_tokens = self._expand_query(query)
        scores = self._index.scores(query_tokens)
        ranked = sorted(
            ((score, index) for index, score in enumerate(scores) if score > 0),
            key=lambda item: (-item[0], item[1]),
        )[:top_k]
        maximum = ranked[0][0] if ranked else 0.0

        results = [
            PolicyEvidence(
                section=self._chunks[index].section,
                page=self._chunks[index].page,
                title=self._chunks[index].title,
                content=self._chunks[index].content,
                relevance_score=round(score / maximum, 4) if maximum else 0.0,
            )
            for score, index in ranked
        ]
        return PolicySearchData(
            results=results,
            requires_human_review=self._requires_review(query),
        )

    def get_policy_conflicts(self, topic: str) -> list[PolicyConflict]:
        """Return known conflicts relevant to a topic identifier or query."""
        normalized = _normalize(topic)
        tokens = set(_tokenize(topic))
        if normalized in POLICY_CONFLICTS:
            return [POLICY_CONFLICTS[normalized]]

        matches: list[PolicyConflict] = []
        if tokens.intersection({"garantia", "defeito", "troca", "fabricante"}):
            matches.append(POLICY_CONFLICTS["warranty_after_30_days"])
        if tokens.intersection({"frete", "entrega"}) and "500" in tokens:
            matches.append(POLICY_CONFLICTS["freight_exactly_500"])
        if tokens.intersection({"email", "mail", "contato"}):
            matches.append(POLICY_CONFLICTS["email_spelling"])
        if tokens.intersection({"whatsapp", "telefone", "celular"}):
            matches.append(POLICY_CONFLICTS["whatsapp_number"])
        if tokens.intersection({"parcelamento", "parcela", "credito"}):
            matches.append(POLICY_CONFLICTS["installment_minimums"])
        return matches

    def requires_human_review(self, topic: str) -> bool:
        """Whether this particular question triggers an unresolved policy case."""
        return self._requires_review(topic)
