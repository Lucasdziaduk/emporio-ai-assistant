"""In-memory conversation state; never persist authentication secrets."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4
from typing import Any


@dataclass
class AgentSession:
    session_id: str = field(default_factory=lambda: str(uuid4()))
    history: list[dict[str, Any]] = field(default_factory=list)
    pending_order_id: int | None = None

    @classmethod
    def new(cls) -> "AgentSession":
        return cls()
