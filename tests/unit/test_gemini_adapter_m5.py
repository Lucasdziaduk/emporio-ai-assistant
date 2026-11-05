from types import SimpleNamespace

from app.llm.gemini_interactions import GeminiInteractionsClient


class FakeStep:
    def __init__(self, payload):
        self.payload = payload
        self.type = payload.get("type")
        self.name = payload.get("name")
        self.id = payload.get("id")
        self.arguments = payload.get("arguments")

    def model_dump(self, **kwargs):
        return self.payload


class FakeInteractions:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            steps=[FakeStep({"type": "function_call", "id": "x1", "name": "search_products", "arguments": {"query": "guitarra"}})],
            output_text="",
        )


def test_gemini_adapter_uses_stateless_interactions_and_extracts_calls():
    interactions = FakeInteractions()
    client = SimpleNamespace(interactions=interactions)
    adapter = GeminiInteractionsClient(api_key="fake-key", client=client)
    history = [{"type": "user_input", "content": [{"type": "text", "text": "guitarra"}]}]
    turn = adapter.generate(history=history, tools=[{"type": "function"}], system_instruction="persona")
    assert interactions.kwargs["store"] is False
    assert interactions.kwargs["model"] == "gemini-3.8-flash"
    assert interactions.kwargs["system_instruction"] == "persona"
    assert turn.tool_calls[0].name == "search_products"
    assert turn.tool_calls[0].arguments == {"query": "guitarra"}
    assert history[0]["content"][0]["text"] == "guitarra"
