"""The six customer-service tools backed exclusively by M2-M4 services."""

from __future__ import annotations

from typing import Any
from dataclasses import asdict, is_dataclass

from app.domain.schemas import (
    GetProductDetailsInput,
    GetPurchaseConditionsInput,
    GetStoreInformationInput,
    GetOrderStatusInput,
    SearchProductsInput,
)
from app.tools.registry import ToolRegistry, ToolSpec


def _json_data(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if is_dataclass(value) and not isinstance(value, type):
        return _json_data(asdict(value))
    if isinstance(value, dict):
        return {str(k): _json_data(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_data(item) for item in value]
    return value


def _success(name: str, data: Any, *, source: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"ok": True, "tool_name": name, "data": _json_data(data)}
    if source:
        result["source"] = {"source_type": source, "snapshot": True}
    return result


def build_store_tool_registry() -> ToolRegistry:
    def search_products(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        request = SearchProductsInput.model_validate(args)
        data = ctx.services.catalog.search_products(request)
        return _success("search_products", data, source="products_csv")

    def get_product_details(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        request = GetProductDetailsInput.model_validate(args)
        data = ctx.services.catalog.get_product_details(request.product_id)
        return _success("get_product_details", data, source="products_csv")

    def get_order_status(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        request = GetOrderStatusInput.model_validate(args)
        # Do not accept a phone number here. Verification happens locally in AgentRuntime.
        ctx.session.pending_order_id = request.order_id
        return _success(
            "get_order_status",
            {
                "verification_required": True,
                "order_id": request.order_id,
                "required_input": "registered_phone_number",
                "privacy_note": "O telefone será verificado localmente e não será enviado ao modelo.",
            },
            source="orders_csv",
        )

    def search_store_policies(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        query = args.get("query")
        top_k = args.get("top_k", 3)
        if not isinstance(query, str) or not 3 <= len(query.strip()) <= 300:
            raise ValueError("Invalid policy query")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 5:
            raise ValueError("Invalid top_k")
        result = ctx.services.policies.search(query, top_k=top_k)
        conflicts = ctx.services.policies.get_policy_conflicts(query)
        data = {
            "results": _json_data(result.results),
            "requires_human_review": bool(result.requires_human_review),
            "conflicts": _json_data(conflicts),
            "evidence_found": bool(result.results),
        }
        return _success("search_store_policies", data, source="policy_manual")

    def get_store_information(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        request = GetStoreInformationInput.model_validate(args)
        data = ctx.services.store_information.get_information(request.topic)
        return _success("get_store_information", data, source="store_information")

    def get_purchase_conditions(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        request = GetPurchaseConditionsInput.model_validate(args)
        data = ctx.services.payments.get_purchase_conditions(request)
        return _success("get_purchase_conditions", data, source="products_csv")

    return ToolRegistry(
        [
            ToolSpec(
                "search_products",
                "Busca instrumentos no catálogo por texto, categoria, faixa de preço e disponibilidade. Use para perguntas sobre produtos, preços e estoque cadastrado.",
                {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Termos do produto; opcional."},
                        "category": {"type": "string", "description": "Categoria exata; opcional."},
                        "min_price_brl": {"type": "number", "minimum": 0},
                        "max_price_brl": {"type": "number", "minimum": 0},
                        "availability": {"type": "string", "enum": ["available", "out_of_stock", "coming_soon", "discontinued", "all"]},
                        "sort_by": {"type": "string", "enum": ["price_asc", "price_desc", "name"]},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 10},
                    },
                }, search_products,
            ),
            ToolSpec(
                "get_product_details",
                "Retorna detalhes, especificações, preço, estoque cadastrado e promoção ativa de um produto já identificado pelo ID.",
                {"type": "object", "properties": {"product_id": {"type": "integer", "minimum": 1}}, "required": ["product_id"]},
                get_product_details,
            ),
            ToolSpec(
                "get_order_status",
                "Inicia a consulta de um pedido pelo número. Nunca solicite nem envie telefone nesta ferramenta; a aplicação pedirá e validará o telefone localmente.",
                {"type": "object", "properties": {"order_id": {"type": "integer", "minimum": 1}}, "required": ["order_id"]},
                get_order_status,
            ),
            ToolSpec(
                "search_store_policies",
                "Pesquisa o manual local da loja para regras de entrega, troca, devolução, garantia, reclamações e demais políticas. Retorna evidências com seção e página.",
                {"type": "object", "properties": {"query": {"type": "string", "minLength": 3}, "top_k": {"type": "integer", "minimum": 1, "maximum": 5}}, "required": ["query"]},
                search_store_policies,
            ),
            ToolSpec(
                "get_store_information",
                "Retorna informações estruturadas da loja: endereço, horário, contato, meios de pagamento ou escopo de produtos.",
                {"type": "object", "properties": {"topic": {"type": "string", "enum": ["address", "opening_hours", "contact", "payment_methods", "store_scope"]}}, "required": ["topic"]},
                get_store_information,
            ),
            ToolSpec(
                "get_purchase_conditions",
                "Calcula condições de pagamento de um produto específico. Use para simular PIX ou parcelamento; as regras são calculadas deterministicamente pelo sistema.",
                {"type": "object", "properties": {"product_id": {"type": "integer", "minimum": 1}, "payment_method": {"type": "string", "enum": ["pix", "credit", "debit", "boleto"]}, "installments": {"type": "integer", "minimum": 1, "maximum": 12}}, "required": ["product_id", "payment_method"]},
                get_purchase_conditions,
            ),
        ]
    )
