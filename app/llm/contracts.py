"""Provider-neutral contracts used by the conversational agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ModelToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelTurn:
    """A single model response, retaining raw steps for stateless replay."""

    steps: list[dict[str, Any]]
    output_text: str = ""
    tool_calls: list[ModelToolCall] = field(default_factory=list)


class ConversationalModel(Protocol):
    def generate(
        self,
        *,
        history: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_instruction: str,
    ) -> ModelTurn: ...
