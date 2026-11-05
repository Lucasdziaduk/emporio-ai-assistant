"""Knowledge-base extraction, chunking, retrieval, and evaluation."""

from app.knowledge.chunker import PolicyChunker
from app.knowledge.conflict_registry import (
    POLICY_CONFLICTS,
    PolicyConflict,
    PolicyConflictRegistry,
)
from app.knowledge.extractor import (
    ExtractedPolicySection,
    PolicyParagraph,
    PolicyPdfExtractor,
)
from app.knowledge.retriever import BM25Retriever, RetrievalHit

__all__ = [
    "BM25Retriever",
    "ExtractedPolicySection",
    "POLICY_CONFLICTS",
    "PolicyChunker",
    "PolicyConflict",
    "PolicyConflictRegistry",
    "PolicyParagraph",
    "PolicyPdfExtractor",
    "RetrievalHit",
]
