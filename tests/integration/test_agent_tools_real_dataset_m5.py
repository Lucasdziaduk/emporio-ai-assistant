"""M5 tool integration against the private challenge dataset."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.data import create_connection, load_dataset
from app.services.container import build_service_container
from app.tools.store_tools import build_store_tool_registry

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "private" / "source"
POLICY = ROOT / "data" / "private" / "store_policies.pdf"
REQUIRED = ["products.csv", "categories.csv", "promotions.csv", "customers.csv", "orders.csv", "order_items.csv"]

pytestmark = pytest.mark.skipif(
    not SOURCE.is_dir() or not POLICY.is_file() or not all((SOURCE / name).is_file() for name in REQUIRED),
    reason="Private challenge CSVs and policy PDF are required for M5 integration tests.",
)


@pytest.fixture
def context():
    connection = create_connection(":memory:")
    load_dataset(SOURCE, connection)
    services = build_service_container(connection, policy_pdf_path=POLICY)
    session = SimpleNamespace(pending_order_id=None)
    yield SimpleNamespace(services=services, session=session)
    connection.close()


def test_product_search_tool_uses_real_catalog_service(context):
    result = build_store_tool_registry().execute(
        "search_products",
        {"category": "Violões", "max_price_brl": 1000, "availability": "available", "limit": 10},
        context,
    )
    assert result["ok"] is True
    assert result["data"]["total_matches"] == 12
    assert result["data"]["returned"] == 10
    assert result["data"]["truncated"] is True


def test_policy_tool_returns_section_page_and_review_flag(context):
    result = build_store_tool_registry().execute(
        "search_store_policies", {"query": "Qual é o WhatsApp principal?", "top_k": 3}, context
    )
    assert result["ok"] is True
    assert result["data"]["evidence_found"] is True
    assert result["data"]["requires_human_review"] is True
    assert all("section" in item and "page" in item for item in result["data"]["results"])
    assert result["data"]["conflicts"][0]["key"] == "whatsapp_number"
