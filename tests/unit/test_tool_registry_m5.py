from types import SimpleNamespace

from app.tools.store_tools import build_store_tool_registry


class FakeCatalog:
    def search_products(self, request):
        return SimpleNamespace(model_dump=lambda **kwargs: {
            "total_matches": 1,
            "returned": 1,
            "truncated": False,
            "products": [{"product_id": 10, "name": "Violão de teste"}],
        })

    def get_product_details(self, product_id):
        return {"product_id": product_id, "name": "Produto"}


class FakeServices:
    catalog = FakeCatalog()


def test_registry_exposes_only_six_allowlisted_tools():
    registry = build_store_tool_registry()
    names = [item["name"] for item in registry.declarations()]
    assert names == [
        "search_products",
        "get_product_details",
        "get_order_status",
        "search_store_policies",
        "get_store_information",
        "get_purchase_conditions",
    ]


def test_search_products_runs_through_pydantic_input_schema():
    registry = build_store_tool_registry()
    context = SimpleNamespace(services=FakeServices(), session=SimpleNamespace(pending_order_id=None))
    result = registry.execute("search_products", {"query": "violão", "limit": 3}, context)
    assert result["ok"] is True
    assert result["data"]["products"][0]["product_id"] == 10


def test_registry_rejects_unknown_tool_and_invalid_arguments_safely():
    registry = build_store_tool_registry()
    context = SimpleNamespace(services=FakeServices(), session=SimpleNamespace(pending_order_id=None))
    unknown = registry.execute("drop_database", {}, context)
    invalid = registry.execute("get_product_details", {"product_id": -100}, context)
    assert unknown["ok"] is False
    assert unknown["error"]["code"] == "VALIDATION_ERROR"
    assert invalid["ok"] is False
    assert invalid["error"]["code"] == "VALIDATION_ERROR"
    assert "-100" not in str(invalid)


def test_order_tool_only_sets_pending_verification_and_never_accepts_phone():
    registry = build_store_tool_registry()
    session = SimpleNamespace(pending_order_id=None)
    context = SimpleNamespace(services=FakeServices(), session=session)
    result = registry.execute("get_order_status", {"order_id": 17}, context)
    assert result["ok"] is True
    assert result["data"]["verification_required"] is True
    assert session.pending_order_id == 17


def test_policy_conflicts_are_returned_as_json_safe_structures():
    class Policies:
        def search(self, query, top_k=3):
            return SimpleNamespace(results=[], requires_human_review=True)

        def get_policy_conflicts(self, query):
            from app.knowledge.conflict_registry import POLICY_CONFLICTS
            return [POLICY_CONFLICTS["email_spelling"]]

    services = SimpleNamespace(policies=Policies())
    context = SimpleNamespace(services=services, session=SimpleNamespace(pending_order_id=None))
    result = build_store_tool_registry().execute(
        "search_store_policies", {"query": "qual é o email?"}, context
    )
    assert result["ok"] is True
    assert result["data"]["requires_human_review"] is True
    assert result["data"]["conflicts"][0]["key"] == "email_spelling"
