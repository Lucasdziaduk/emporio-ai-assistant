"""Allow-listed function registry for model-requested tool calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from pydantic import ValidationError

from app.domain.errors import AppError


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict[str, Any], Any], dict[str, Any]]

    def declaration(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    def __init__(self, tools: list[ToolSpec]) -> None:
        self._tools: dict[str, ToolSpec] = {}
        for tool in tools:
            if tool.name in self._tools:
                raise ValueError(f"Duplicate tool name: {tool.name}")
            self._tools[tool.name] = tool

    def declarations(self) -> list[dict[str, Any]]:
        return [tool.declaration() for tool in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, Any], context: Any) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            return {
                "ok": False,
                "tool_name": name or "unknown",
                "error": {"code": "VALIDATION_ERROR", "message": "Ferramenta não permitida."},
            }
        if not isinstance(arguments, dict):
            arguments = {}
        try:
            return tool.handler(arguments, context)
        except AppError as exc:
            return {"ok": False, "tool_name": name, "error": exc.to_tool_error().model_dump(mode="json")}
        except ValidationError:
            return {
                "ok": False,
                "tool_name": name,
                "error": {"code": "VALIDATION_ERROR", "message": "Os parâmetros informados são inválidos."},
            }
        except (TypeError, ValueError):
            return {
                "ok": False,
                "tool_name": name,
                "error": {"code": "VALIDATION_ERROR", "message": "Não foi possível validar os parâmetros informados."},
            }
        except Exception:
            # Never leak SQL, customer fields, filesystem paths, or tracebacks to the model.
            return {
                "ok": False,
                "tool_name": name,
                "error": {"code": "INTERNAL_ERROR", "message": "O serviço não conseguiu concluir a consulta."},
            }
