from pathlib import Path

import pytest

from app.knowledge.evaluation import GOLDEN_CASES, evaluate_retrieval
from app.services.policy_service import PolicyService


def test_golden_evaluation_has_24_cases_and_full_recall_at_three():
    pdf = Path(__file__).resolve().parents[2] / "data" / "private" / "store_policies.pdf"
    if not pdf.is_file():
        pytest.skip("Original policy PDF is not present in data/private.")
    report = evaluate_retrieval(PolicyService(pdf), GOLDEN_CASES, top_k=3)
    assert report["case_count"] == 24
    assert report["hits"] == 24
    assert report["recall_at_k"] == 1.0
    assert report["mrr"] >= 0.95
