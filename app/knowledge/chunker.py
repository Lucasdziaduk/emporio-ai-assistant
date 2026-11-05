"""Section-aware paragraph chunking for policy evidence."""

from __future__ import annotations

import re
from typing import Iterable, Sequence

from app.domain.schemas import PolicyEvidence
from app.knowledge.extractor import ExtractedPolicySection, PolicyParagraph
from app.knowledge.tokenizer import tokenize


class PolicyChunker:
    """Build retrieval chunks without crossing policy section boundaries."""

    def __init__(self, *, max_tokens: int = 180, min_tokens: int = 1) -> None:
        if max_tokens < 20:
            raise ValueError("max_tokens must be at least 20.")
        if min_tokens < 1 or min_tokens > max_tokens:
            raise ValueError("min_tokens must be between 1 and max_tokens.")
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens

    def chunk_sections(
        self,
        sections: Sequence[ExtractedPolicySection],
    ) -> list[PolicyEvidence]:
        chunks: list[PolicyEvidence] = []
        for section in sections:
            paragraphs: list[PolicyParagraph] = []
            token_total = 0
            active_page: int | None = None

            def flush() -> None:
                nonlocal paragraphs, token_total, active_page
                if not paragraphs:
                    return
                content = "\n\n".join(item.text for item in paragraphs).strip()
                if content:
                    chunks.append(PolicyEvidence(
                        section=section.section,
                        page=active_page or section.page,
                        title=section.title,
                        content=content,
                    ))
                paragraphs = []
                token_total = 0
                active_page = None

            for paragraph in section.paragraphs:
                pieces = self._split_if_oversized(paragraph)
                for piece in pieces:
                    piece_tokens = len(tokenize(piece.text))
                    if paragraphs and (
                        piece.page != active_page
                        or token_total + piece_tokens > self.max_tokens
                    ):
                        flush()
                    if not paragraphs:
                        active_page = piece.page
                    paragraphs.append(piece)
                    token_total += piece_tokens
            flush()
        return chunks

    def chunk_evidence(self, evidence: Sequence[PolicyEvidence]) -> list[PolicyEvidence]:
        """Re-chunk existing evidence objects when a caller already has passages."""
        from app.knowledge.extractor import ExtractedPolicySection

        sections = [
            ExtractedPolicySection(
                section=item.section,
                title=item.title,
                page=item.page,
                paragraphs=tuple(
                    PolicyParagraph(page=item.page, text=paragraph)
                    for paragraph in self._split_paragraphs(item.content)
                ),
            )
            for item in evidence
        ]
        return self.chunk_sections(sections)

    def _split_if_oversized(self, paragraph: PolicyParagraph) -> list[PolicyParagraph]:
        if len(tokenize(paragraph.text)) <= self.max_tokens:
            return [paragraph]
        sentences = re.split(r"(?<=[.!?;])\s+", paragraph.text)
        output: list[PolicyParagraph] = []
        current: list[str] = []
        count = 0
        for sentence in sentences:
            sentence_count = len(tokenize(sentence))
            if current and count + sentence_count > self.max_tokens:
                output.append(PolicyParagraph(page=paragraph.page, text=" ".join(current)))
                current, count = [], 0
            if sentence_count > self.max_tokens:
                words = sentence.split()
                window: list[str] = []
                for word in words:
                    if len(tokenize(" ".join(window + [word]))) > self.max_tokens and window:
                        output.append(PolicyParagraph(page=paragraph.page, text=" ".join(window)))
                        window = [word]
                    else:
                        window.append(word)
                if window:
                    if current:
                        output.append(PolicyParagraph(page=paragraph.page, text=" ".join(current)))
                        current, count = [], 0
                    output.append(PolicyParagraph(page=paragraph.page, text=" ".join(window)))
            else:
                current.append(sentence)
                count += sentence_count
        if current:
            output.append(PolicyParagraph(page=paragraph.page, text=" ".join(current)))
        return output

    @staticmethod
    def _split_paragraphs(content: str) -> list[str]:
        return [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
