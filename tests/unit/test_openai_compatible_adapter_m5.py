from types import SimpleNamespace

from app.llm.openai_compatible import OpenAICompatibleToolClient


class FakeCompletions:
    def __init__(self, messages):
        self.messages = messages
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.messages == ["tool-call"]:
            tool_call = SimpleNamespace(
                id="call_123",
                function=SimpleNamespace(
                    name="search_products",
                    arguments='{"query":"violao"}',
                ),
            )
            message = SimpleNamespace(content=None, tool_calls=[tool_call], refusal=None)
        else:
            message = SimpleNamespace(content="Encontrei algumas opções.", tool_calls=[], refusal=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=FakeCompletions([]))


def test_adapter_converts_tool_schema_and_extracts_tool_calls():
    client = FakeClient()
    adapter = OpenAICompatibleToolClient(
        api_key="fake",
        model_name="openai/gpt-oss-20b",
        client=client,
    )
    tools = [
        {
            "type": "function",
            "name": "search_products",
            "description": "Search products",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
        }
    ]
    client.chat.completions.messages = ["tool-call"]

    turn = adapter.generate(
        history=[{"type": "user_input", "content": [{"type": "text", "text": "Quero violão"}]}],
        tools=tools,
        system_instruction="You are a shop assistant.",
    )

    assert client.chat.completions.kwargs["model"] == "openai/gpt-oss-20b"
    assert client.chat.completions.kwargs["messages"][1] == {"role": "user", "content": "Quero violão"}
    assert client.chat.completions.kwargs["tools"][0]["function"]["name"] == "search_products"
    assert turn.tool_calls[0].name == "search_products"
    assert turn.tool_calls[0].arguments == {"query": "violao"}
    assert turn.steps[0]["type"] == "function_call"


def test_adapter_reconstructs_tool_result_history_and_returns_final_text():
    client = FakeClient()
    adapter = OpenAICompatibleToolClient(api_key="fake", model_name="openai/gpt-oss-20b", client=client)
    history = [
        {"type": "user_input", "content": [{"type": "text", "text": "Quero violão"}]},
        {"type": "function_call", "id": "call_123", "name": "search_products", "arguments": {"query": "violao"}},
        {"type": "function_result", "name": "search_products", "call_id": "call_123", "result": [{"type": "text", "text": '{"ok":true}'}]},
    ]
    client.chat.completions.messages = ["final-answer"]

    turn = adapter.generate(history=history, tools=[], system_instruction="System prompt")

    messages = client.chat.completions.kwargs["messages"]
    assert [item["role"] for item in messages] == ["system", "user", "assistant", "tool"]
    assert messages[-1]["tool_call_id"] == "call_123"
    assert messages[-1]["content"] == '{"ok":true}'
    assert turn.output_text == "Encontrei algumas opções."
    assert turn.steps == [{"type": "text", "text": "Encontrei algumas opções."}]


def test_adapter_keeps_multiple_consecutive_tool_calls_in_one_assistant_message():
    history = [
        {"type": "function_call", "id": "a", "name": "first", "arguments": {"x": 1}},
        {"type": "function_call", "id": "b", "name": "second", "arguments": {"y": 2}},
    ]
    messages = OpenAICompatibleToolClient._history_to_messages(history)
    assert len(messages) == 1
    assert messages[0]["role"] == "assistant"
    assert len(messages[0]["tool_calls"]) == 2
