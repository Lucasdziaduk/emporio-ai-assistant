"""Adapter for OpenAI-compatible chat-completions APIs (Groq default)."""

from __future__ import annotations

import json
from typing import Any

from app.llm.contracts import ModelToolCall, ModelTurn


class OpenAICompatibleToolClient:
    """Provider-neutral adapter for local function calling over chat completions.

    The agent's internal history uses a small provider-neutral subset of the
    Gemini Interactions format. This adapter translates that history to the
    OpenAI chat-completions message format and translates tool calls back.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        base_url: str = "https://api.groq.com/openai/v1",
        timeout: float = 25.0,
        max_retries: int = 1,
        client: Any | None = None,
    ) -> None:
        if not api_key and client is None:
            raise ValueError("An API key is required.")
        if not model_name.strip():
            raise ValueError("model_name cannot be empty.")
        if timeout <= 0:
            raise ValueError("timeout must be positive.")
        self.model_name = model_name
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise RuntimeError(
                    "Instale a dependência openai com requirements-m5-groq.txt."
                ) from exc
            client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
                max_retries=max_retries,
            )
        self.client = client

    def generate(
        self,
        *,
        history: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_instruction: str,
    ) -> ModelTurn:
        messages = [{"role": "system", "content": system_instruction}]
        messages.extend(self._history_to_messages(history))
        provider_tools = [self._tool_to_openai(tool) for tool in tools]

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=provider_tools or None,
            tool_choice="auto" if provider_tools else "none",
        )
        choices = getattr(response, "choices", None) or []
        if not choices:
            return ModelTurn(steps=[], output_text="")

        message = choices[0].message
        raw_calls = getattr(message, "tool_calls", None) or []
        calls: list[ModelToolCall] = []
        steps: list[dict[str, Any]] = []
        for index, raw_call in enumerate(raw_calls):
            function = getattr(raw_call, "function", None)
            name = str(getattr(function, "name", "") or "")
            raw_arguments = getattr(function, "arguments", "{}") or "{}"
            try:
                arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
            except (TypeError, json.JSONDecodeError):
                arguments = {}
            if not isinstance(arguments, dict):
                arguments = {}
            call_id = str(getattr(raw_call, "id", "") or f"call_{index}")
            call = ModelToolCall(call_id=call_id, name=name, arguments=arguments)
            calls.append(call)
            steps.append(
                {
                    "type": "function_call",
                    "id": call.call_id,
                    "name": call.name,
                    "arguments": call.arguments,
                }
            )

        content = getattr(message, "content", None)
        if isinstance(content, list):
            content = "".join(
                str(part.get("text", "")) for part in content if isinstance(part, dict)
            )
        output_text = str(content or getattr(message, "refusal", None) or "")
        if not calls and output_text:
            steps.append({"type": "text", "text": output_text})
        return ModelTurn(steps=steps, output_text=output_text, tool_calls=calls)

    @staticmethod
    def _tool_to_openai(tool: dict[str, Any]) -> dict[str, Any]:
        # M5's registry declares Gemini-style flat function definitions.
        if tool.get("type") == "function" and "function" in tool:
            return tool
        return {
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters") or {"type": "object", "properties": {}},
            },
        }

    @classmethod
    def _history_to_messages(cls, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        index = 0
        while index < len(history):
            step = history[index]
            kind = step.get("type")

            if kind == "user_input":
                content = cls._text_content(step.get("content"))
                if content:
                    messages.append({"role": "user", "content": content})
                index += 1
                continue

            if kind == "text":
                content = str(step.get("text") or "")
                if content:
                    messages.append({"role": "assistant", "content": content})
                index += 1
                continue

            if kind == "function_call":
                tool_calls: list[dict[str, Any]] = []
                while index < len(history) and history[index].get("type") == "function_call":
                    call = history[index]
                    arguments = call.get("arguments") or {}
                    if not isinstance(arguments, str):
                        arguments = json.dumps(arguments, ensure_ascii=False, separators=(",", ":"))
                    tool_calls.append(
                        {
                            "id": str(call.get("id") or "call_missing_id"),
                            "type": "function",
                            "function": {
                                "name": str(call.get("name") or ""),
                                "arguments": arguments,
                            },
                        }
                    )
                    index += 1
                messages.append({"role": "assistant", "tool_calls": tool_calls})
                continue

            if kind == "function_result":
                result_content = cls._text_content(step.get("result"))
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": str(step.get("call_id") or "call_missing_id"),
                        "name": str(step.get("name") or "unknown_tool"),
                        "content": result_content or "{}",
                    }
                )
                index += 1
                continue

            # Unknown provider-specific steps are ignored rather than leaked
            # into an incompatible provider's request schema.
            index += 1
        return messages

    @staticmethod
    def _text_content(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            chunks: list[str] = []
            for item in value:
                if isinstance(item, dict) and item.get("type") == "text":
                    chunks.append(str(item.get("text") or ""))
            return "\n".join(chunk for chunk in chunks if chunk)
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False, default=str)
        return ""
