"""Google Gemini Interactions API adapter with client-managed history."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.llm.contracts import ModelToolCall, ModelTurn


class GeminiInteractionsClient:
    """Thin adapter around google-genai; no server-side interaction storage."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str = "gemini-3.8-flash",
        client: Any | None = None,
    ) -> None:
        if not api_key and client is None:
            raise ValueError("GEMINI_API_KEY is required.")
        if not model_name.strip():
            raise ValueError("model_name cannot be empty.")
        self.model_name = model_name
        if client is None:
            try:
                from google import genai
            except ImportError as exc:  # pragma: no cover - depends on optional SDK
                raise RuntimeError(
                    "Instale a dependência google-genai para usar o Gemini."
                ) from exc
            client = genai.Client(api_key=api_key)
        self.client = client

    def generate(
        self,
        *,
        history: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_instruction: str,
    ) -> ModelTurn:
        response = self.client.interactions.create(
            model=self.model_name,
            store=False,
            input=deepcopy(history),
            tools=deepcopy(tools),
            system_instruction=system_instruction,
        )
        steps: list[dict[str, Any]] = []
        calls: list[ModelToolCall] = []
        for step in getattr(response, "steps", []) or []:
            raw = step.model_dump(mode="json", exclude_none=True) if hasattr(step, "model_dump") else dict(step)
            steps.append(raw)
            step_type = raw.get("type")
            if step_type == "function_call":
                arguments = raw.get("arguments") or {}
                if not isinstance(arguments, dict):
                    arguments = {}
                calls.append(
                    ModelToolCall(
                        call_id=str(raw.get("id") or ""),
                        name=str(raw.get("name") or ""),
                        arguments=arguments,
                    )
                )
        output_text = getattr(response, "output_text", "") or ""
        return ModelTurn(steps=steps, output_text=output_text, tool_calls=calls)
