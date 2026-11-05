"""Dependency-light BM25 retrieval with conservative evidence filtering."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from app.domain.schemas import PolicyEvidence
from app.knowledge.tokenizer import expand_query, tokenize


@dataclass(frozen=True)
class RetrievalHit:
    evidence: PolicyEvidence
    raw_score: float
    normalized_score: float
    matched_terms: tuple[str, ...]


class BM25Retriever:
    """BM25 index designed for a small, sectioned Portuguese policy manual."""

    def __init__(
        self,
        documents: Sequence[PolicyEvidence],
        *,
        k1: float = 1.5,
        b: float = 0.75,
        min_raw_score: float = 0.05,
        max_per_section: int = 2,
    ) -> None:
        if not documents:
            raise ValueError("At least one policy evidence chunk is required.")
        if k1 <= 0 or not 0 <= b <= 1:
            raise ValueError("Invalid BM25 parameters.")
        if min_raw_score < 0 or max_per_section < 1:
            raise ValueError("Invalid retrieval thresholds.")

        self.documents = list(documents)
        self.k1 = k1
        self.b = b
        self.min_raw_score = min_raw_score
        self.max_per_section = max_per_section
        self.tokens = [
            tokenize(f"{item.section} {item.title} {item.content}")
            for item in self.documents
        ]
        self.term_frequencies = [Counter(tokens) for tokens in self.tokens]
        self.document_frequency: Counter[str] = Counter()
        for frequencies in self.term_frequencies:
            self.document_frequency.update(frequencies.keys())
        self.document_count = len(self.documents)
        self.average_length = (
            sum(len(tokens) for tokens in self.tokens) / self.document_count
        )
        self.idf = {
            token: math.log(1 + (self.document_count - frequency + 0.5) / (frequency + 0.5))
            for token, frequency in self.document_frequency.items()
        }

    def search(self, query: str, *, top_k: int = 3) -> list[RetrievalHit]:
        if not isinstance(query, str) or len(query.strip()) < 3:
            raise ValueError("Policy query must contain at least three characters.")
        if not 1 <= top_k <= 5:
            raise ValueError("top_k must be between 1 and 5.")

        base_terms = tokenize(query)
        expanded_terms = expand_query(query)
        if not expanded_terms:
            return []
        # Query terms stated by the customer carry more weight than added synonyms.
        # This improves precision for phrases such as "o que a garantia não cobre".
        term_weights = {term: 1.8 for term in base_terms}
        for term in expanded_terms:
            term_weights.setdefault(term, 0.55)

        scored: list[tuple[float, int, tuple[str, ...]]] = []
        for index, frequencies in enumerate(self.term_frequencies):
            doc_length = len(self.tokens[index])
            score = 0.0
            matched: list[str] = []
            for term in expanded_terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                matched.append(term)
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * (doc_length / self.average_length if self.average_length else 0)
                )
                score += term_weights[term] * self.idf.get(term, 0.0) * (
                    frequency * (self.k1 + 1) / denominator
                )
            if score >= self.min_raw_score and matched:
                scored.append((score, index, tuple(dict.fromkeys(matched))))

        if not scored:
            return []

        scored.sort(key=lambda item: (-item[0], item[1]))
        maximum = scored[0][0]
        hits: list[RetrievalHit] = []
        section_counts: Counter[str] = Counter()
        for raw_score, index, matched in scored:
            section = self.documents[index].section
            if section_counts[section] >= self.max_per_section:
                continue
            normalized = min(1.0, raw_score / maximum) if maximum else 0.0
            evidence = self.documents[index].model_copy(
                update={"relevance_score": round(normalized, 4)}
            )
            hits.append(RetrievalHit(
                evidence=evidence,
                raw_score=raw_score,
                normalized_score=normalized,
                matched_terms=matched,
            ))
            section_counts[section] += 1
            if len(hits) >= top_k:
                break
        return hits

    def retrieve(self, query: str, *, top_k: int = 3) -> list[PolicyEvidence]:
        """Return evidence only, retaining the M3 service's simple interface."""
        return [hit.evidence for hit in self.search(query, top_k=top_k)]
