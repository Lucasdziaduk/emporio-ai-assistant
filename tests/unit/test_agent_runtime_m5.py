from datetime import date
from types import SimpleNamespace

from app.agent import AgentRuntime, AgentSession
from app.agent.security import contains_phone_like_value, redact_phone_like_values
from app.domain.enums import OrderStatus
from app.domain.schemas import OrderItemSummary, OrderStatusData
from app.llm.contracts import ModelToolCall, ModelTurn


class FakeModel:
    def __init__(self, turns):
        self.turns = list(turns)
        self.received_histories = []

    def generate(self, *, history, tools, system_instruction):
        import copy
        self.received_histories.append(copy.deepcopy(history))
        assert len(tools) == 6
        assert "Empório da Música" in system_instruction
        return self.turns.pop(0)


class FakeIdentity:
    def __init__(self, correct_phone="67987654321", attempts=3):
        self.correct_phone = correct_phone
        self.remaining = attempts
        self.seen_values = []

    def verify_order_access(self, order_id, phone, *, session_id):
        from pydantic import SecretStr
        from app.domain.errors import AuthenticationFailedError
        value = phone.get_secret_value() if isinstance(phone, SecretStr) else str(phone)
        self.seen_values.append(value)
        if "".join(ch for ch in value if ch.isdigit()) != self.correct_phone:
            self.remaining -= 1
            raise AuthenticationFailedError()
        return SimpleNamespace(order_id=order_id, session_id=session_id)

    def attempts_remaining(self, session_id):
        return max(0, self.remaining)


class FakeOrders:
    def get_order_status(self, order_id, *, authorization, session_id):
        assert authorization.order_id == order_id
        return OrderStatusData(
            order_id=order_id,
            status=OrderStatus.SHIPPED,
            order_date=date(2026, 3, 1),
            tracking_code="BR123456789",
            estimated_delivery=date(2026, 3, 7),
            items=[OrderItemSummary(product_id=99, product_name="Violão", quantity=1)],
            dataset_is_static=True,
            latest_order_date_in_dataset=date(2026, 3, 22),
        )


def test_tool_call_is_executed_then_model_writes_customer_response():
    model = FakeModel([
        ModelTurn(
            steps=[{"type": "function_call", "id": "call-1", "name": "search_products", "arguments": {"query": "violão"}}],
            tool_calls=[ModelToolCall("call-1", "search_products", {"query": "violão"})],
        ),
        ModelTurn(steps=[{"type": "model_output", "content": [{"type": "text", "text": "Encontrei opções."}]}], output_text="Encontrei opções."),
    ])
    catalog = SimpleNamespace(search_products=lambda req: SimpleNamespace(model_dump=lambda **kw: {"returned": 0, "products": []}))
    services = SimpleNamespace(catalog=catalog)
    agent = AgentRuntime(services=services, model=model)
    session = AgentSession.new()
    assert agent.respond(session, "Tem violão?") == "Encontrei opções."
    assert any(item.get("type") == "function_result" for item in session.history)
    assert len(model.received_histories) == 2


def test_phone_is_redacted_before_non_order_message_reaches_model():
    model = FakeModel([ModelTurn(steps=[{"type": "model_output"}], output_text="Certo, posso ajudar com a loja.")])
    services = SimpleNamespace()
    agent = AgentRuntime(services=services, model=model)
    session = AgentSession.new()
    message = "Meu telefone é (67) 98765-4321. Vocês abrem sábado?"
    response = agent.respond(session, message)
    assert response.startswith("Certo")
    history_text = str(session.history) + str(model.received_histories)
    assert "98765-4321" not in history_text
    assert "67987654321" not in history_text
    assert "telefone removido" in history_text


def test_order_phone_is_validated_locally_and_never_added_to_llm_history():
    model = FakeModel([
        ModelTurn(
            steps=[{"type": "function_call", "id": "call-order", "name": "get_order_status", "arguments": {"order_id": 1}}],
            tool_calls=[ModelToolCall("call-order", "get_order_status", {"order_id": 1})],
        ),
        ModelTurn(steps=[{"type": "model_output", "content": [{"type": "text", "text": "Informe o telefone cadastrado."}]}], output_text="Informe o telefone cadastrado."),
    ])
    identity = FakeIdentity()
    services = SimpleNamespace(identity=identity, orders=FakeOrders())
    agent = AgentRuntime(services=services, model=model)
    session = AgentSession.new()
    assert agent.respond(session, "Quero consultar o pedido 1") == "Informe o telefone cadastrado."
    assert session.pending_order_id == 1
    result = agent.respond(session, "(67) 98765-4321")
    assert "pedido **#1**" in result
    assert "não é uma atualização em tempo real" in result
    assert session.pending_order_id is None
    combined_history = str(session.history) + str(model.received_histories)
    assert "98765-4321" not in combined_history
    assert "67987654321" not in combined_history
    assert identity.seen_values == ["(67) 98765-4321"]


def test_unrelated_phone_message_is_not_sent_to_model():
    model = FakeModel([ModelTurn(steps=[{"type": "model_output"}], output_text="ok")])
    agent = AgentRuntime(services=SimpleNamespace(), model=model)
    response = agent.respond(AgentSession.new(), "11987654321")
    assert "número do pedido" in response
    assert model.received_histories == []


def test_phone_redaction_helpers_cover_brazilian_mobile_numbers():
    text = "Ligue para 11 98765-4321, por favor."
    assert contains_phone_like_value(text)
    assert "11 98765-4321" not in redact_phone_like_values(text)


def test_three_failed_phone_attempts_lock_order_lookup():
    model = FakeModel([
        ModelTurn(
            steps=[{"type": "function_call", "id": "call-order", "name": "get_order_status", "arguments": {"order_id": 1}}],
            tool_calls=[ModelToolCall("call-order", "get_order_status", {"order_id": 1})],
        ),
        ModelTurn(steps=[{"type": "model_output"}], output_text="Informe o telefone cadastrado."),
    ])
    identity = FakeIdentity(correct_phone="67987654321", attempts=3)
    services = SimpleNamespace(identity=identity, orders=FakeOrders())
    agent = AgentRuntime(services=services, model=model)
    session = AgentSession.new()
    agent.respond(session, "Quero consultar pedido 1")
    agent.respond(session, "11111111111")
    agent.respond(session, "22222222222")
    final = agent.respond(session, "33333333333")
    assert "consulta foi bloqueada" in final
    assert session.pending_order_id is None
    assert len(identity.seen_values) == 3


def test_phone_with_keyword_is_redacted_even_without_area_code():
    message = "Meu telefone é 98765432."
    assert contains_phone_like_value(message)
    assert "98765432" not in redact_phone_like_values(message)


def test_unresolved_policy_conflict_is_enforced_without_another_llm_turn():
    from app.knowledge.conflict_registry import POLICY_CONFLICTS

    model = FakeModel([
        ModelTurn(
            steps=[{
                "type": "function_call",
                "id": "policy-call",
                "name": "search_store_policies",
                "arguments": {"query": "Como funciona a política de troca e devolução?"},
            }],
            tool_calls=[ModelToolCall(
                "policy-call",
                "search_store_policies",
                {"query": "Como funciona a política de troca e devolução?"},
            )],
        ),
        # This turn must never be requested: runtime enforces the conflict gate.
        ModelTurn(steps=[{"type": "text", "text": "Resposta inventada."}], output_text="Resposta inventada."),
    ])

    class FakePolicies:
        def search(self, query, top_k=3):
            return SimpleNamespace(results=[], requires_human_review=True)

        def get_policy_conflicts(self, query):
            return [POLICY_CONFLICTS["warranty_after_30_days"]]

    agent = AgentRuntime(
        services=SimpleNamespace(policies=FakePolicies()),
        model=model,
    )
    session = AgentSession.new()
    answer = agent.respond(session, "Como funciona a política de troca e devolução?")

    assert "seção 4.2 (página 4)" in answer
    assert "seção 8.1 (página 7)" in answer
    assert "não vou afirmar que a cobertura termina após 30 dias" in answer
    assert "Resposta inventada" not in answer
    assert len(model.received_histories) == 1
    assert any(item.get("type") == "function_result" for item in session.history)
    assert any(item.get("type") == "text" and answer in item.get("text", "") for item in session.history)


def test_product_details_are_formatted_from_source_fields_without_llm_reinterpretation():
    product_data = {
        "product_id": 81,
        "name": "Yamaha C40 Nylon Natural",
        "category": "Violões",
        "status": "active",
        "availability": "available",
        "price_cents": 59990,
        "formatted_price": "R$ 599,90",
        "stock_quantity": 12,
        "description": "Violão clássico com tampo em Spruce e fundo/laterais em Meranti.",
        "specs": {
            "top": "Spruce",
            "back_sides": "Meranti",
            "neck": "Nato",
            "strings": "nylon",
            "scale": "650mm",
            "electronics": "no",
            "color": "Natural",
        },
        "created_at": "2021-03-15",
        "promotion": None,
    }

    class FakeCatalog:
        def get_product_details(self, product_id):
            assert product_id == 81
            return SimpleNamespace(model_dump=lambda **kwargs: product_data)

    model = FakeModel([
        ModelTurn(
            steps=[{
                "type": "function_call",
                "id": "product-details-call",
                "name": "get_product_details",
                "arguments": {"product_id": 81},
            }],
            tool_calls=[ModelToolCall(
                "product-details-call", "get_product_details", {"product_id": 81}
            )],
        ),
        # The runtime should not request another LLM response for this simple lookup.
        ModelTurn(steps=[{"type": "text", "text": "Madeira da escala: Nato"}], output_text="Madeira da escala: Nato"),
    ])
    agent = AgentRuntime(services=SimpleNamespace(catalog=FakeCatalog()), model=model)
    session = AgentSession.new()

    answer = agent.respond(session, "Quais são as especificações do Yamaha C40, ID 81?")

    assert "Braço: Nato" in answer
    assert "Comprimento da escala: 650mm" in answer
    assert "Madeira da escala" not in answer
    assert "Sistema eletrônico: Não" in answer
    assert "snapshot do catálogo" in answer
    assert len(model.received_histories) == 1
