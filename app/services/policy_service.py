"""Public policy-service facade backed by the M4 knowledge pipeline.

This module intentionally preserves the M3 PolicyService API so the service
container and existing callers do not need to change.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from app.domain.errors import SourceUnavailableError
from app.domain.schemas import PolicyEvidence, PolicySearchData
from app.knowledge.chunker import PolicyChunker
from app.knowledge.conflict_registry import (
    POLICY_CONFLICTS,
    PolicyConflict,
    PolicyConflictRegistry,
)
from app.knowledge.extractor import PolicyPdfExtractor
from app.knowledge.retriever import BM25Retriever


class PolicyService:
    """Extract, index, and retrieve policy evidence from the local manual."""

    def __init__(
        self,
        policy_pdf_path: str | Path | None = None,
        *,
        chunks: Sequence[PolicyEvidence] | None = None,
        min_raw_score: float = 0.05,
    ) -> None:
        self.policy_pdf_path = Path(policy_pdf_path) if policy_pdf_path else None
        self._chunks: list[PolicyEvidence] = list(chunks or [])
        self._retriever: BM25Retriever | None = None
        self._extractor = PolicyPdfExtractor()
        self._chunker = PolicyChunker()
        self._conflicts = PolicyConflictRegistry()
        self._min_raw_score = min_raw_score
        if self._chunks:
            self._build_index()

    @classmethod
    def extract_policy_chunks(cls, pdf_path: str | Path) -> list[PolicyEvidence]:
        """Compatibility method retained from M3; returns section-aware chunks."""
        sections = PolicyPdfExtractor().extract(pdf_path)
        return PolicyChunker().chunk_sections(sections)

    def load(self) -> None:
        """Load the PDF once and build the retrieval index."""
        if self._retriever is not None:
            return
        if self._chunks:
            self._build_index()
            return
        if self.policy_pdf_path is None:
            raise SourceUnavailableError()
        sections = self._extractor.extract(self.policy_pdf_path)
        self._chunks = self._chunker.chunk_sections(sections)
        if not self._chunks:
            raise SourceUnavailableError()
        self._build_index()

    def _build_index(self) -> None:
        if not self._chunks:
            raise SourceUnavailableError()
        self._retriever = BM25Retriever(
            self._chunks,
            min_raw_score=self._min_raw_score,
            max_per_section=2,
        )

    @property
    def chunks(self) -> tuple[PolicyEvidence, ...]:
        """Read-only snapshot of indexed evidence for diagnostics and tests."""
        if self._retriever is None:
            self.load()
        return tuple(self._chunks)

    def search(self, query: str, top_k: int = 3) -> PolicySearchData:
        """Retrieve ranked, page-cited evidence and flag known ambiguities."""
        if not isinstance(query, str) or len(query.strip()) < 3:
            raise ValueError("Policy query must contain at least three characters.")
        if not 1 <= top_k <= 5:
            raise ValueError("top_k must be between 1 and 5.")
        if self._retriever is None:
            self.load()
        assert self._retriever is not None
        results = self._retriever.retrieve(query, top_k=top_k)
        return PolicySearchData(
            results=results,
            requires_human_review=self.requires_human_review(query),
        )

    def get_policy_conflicts(self, topic: str) -> list[PolicyConflict]:
        """Return documented policy conflicts related to a topic or query."""
        return self._conflicts.get_conflicts(topic)

    def requires_human_review(self, topic: str) -> bool:
        """Return whether the current question matches an unresolved ambiguity."""
        return self._conflicts.requires_human_review(topic)

    def evaluate(self, *, top_k: int = 3) -> dict:
        """Run the bundled retrieval evaluation set against this manual."""
        from app.knowledge.evaluation import evaluate_retrieval
        return evaluate_retrieval(self, top_k=top_k)
