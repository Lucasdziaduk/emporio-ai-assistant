"""Run the bundled retrieval evaluation.

Usage:
    python -m app.knowledge
    python -m app.knowledge path/to/store_policies.pdf
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.services.policy_service import PolicyService


def main() -> int:
    pdf_path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path.cwd() / "data" / "private" / "store_policies.pdf"
    )
    service = PolicyService(pdf_path)
    report = service.evaluate(top_k=3)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["recall_at_k"] >= 0.90 else 1


if __name__ == "__main__":
    raise SystemExit(main())
