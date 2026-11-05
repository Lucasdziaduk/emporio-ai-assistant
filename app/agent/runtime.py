"""Conversation orchestration with deterministic tools and local order verification."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import SecretStr, ValidationError

from app.agent.prompt import SYSTEM_PROMPT
from app.agent.security import (
    contains_phone_like_value,
    looks_like_cancel,
    normalize_phone_input,
    redact_phone_like_values,
)
from app.agent.session import AgentSession
from app.domain.errors import AuthenticationFailedError, AppError
from app.llm.contracts import ConversationalModel, ModelToolCall, ModelTurn
from app.tools.registry import ToolRegistry
from app.tools.store_tools import build_store_tool_registry


@dataclass
class ToolContext:
    services: Any
    session: AgentSession


class AgentRuntime:
    def __init__(
        self,
        *,
        services: Any,
        model: ConversationalModel,
        tool_registry: ToolRegistry | None = None,
        max_tool_calls: int = 8,
    ) -> None:
        if max_tool_calls < 1:
            raise ValueError("max_tool_calls must be positive.")
        self.services = services
        self.model = model
        self.registry = tool_registry or build_store_tool_registry()
        self.max_tool_calls = max_tool_calls

    def respond(self, session: AgentSession, user_message: str) -> str:
        """Return one safe response; order-phone input is handled without the LLM."""
        if not isinstance(user_message, str) or not user_message.strip():
            return "Pode me dizer como posso ajudar?"

        message = user_message.strip()
        if session.pending_order_id is not None:
            return self._handle_pending_order_verification(session, message)

        if contains_phone_like_value(message):
            safe_message = redact_phone_like_values(message)
            if safe_message == "[telefone removido por privacidade]":
                return "Para consultar um pedido, informe primeiro o número do pedido. O telefone cadastrado será solicitado e validado localmente."
            message = safe_message

        session.history.append(
            {"type": "user_input", "content": [{"type": "text", "text": message}]}
        )
        context = ToolContext(services=self.services, session=session)
        tool_calls_used = 0

        while True:
            try:
                turn = self.model.generate(
                    history=session.history,
                    tools=self.registry.declarations(),
                    system_instruction=SYSTEM_PROMPT,
                )
            except Exception:
                return "Desculpe, não consegui acessar o atendimento inteligente neste momento. Tente novamente em instantes."

            for step in turn.steps:
                session.history.append(step)

            calls = turn.tool_calls or self._extract_calls(turn.steps)
            if not calls:
                answer = turn.output_text.strip()
                return answer or "Não consegui formular uma resposta segura. Pode reformular sua pergunta?"

            if tool_calls_used + len(calls) > self.max_tool_calls:
                # Pair every model-issued call with a result so the stateless
                # provider history is valid on the next user turn. No handler runs.
                for call in calls:
                    session.history.append({
                        "type": "function_result",
                        "name": call.name,
                        "call_id": call.call_id,
                        "result": [{
                            "type": "text",
                            "text": json.dumps({
                                "ok": False,
                                "error": {"code": "TOOL_LIMIT", "message": "Limite de consultas por turno atingido."},
                            }, ensure_ascii=False),
                        }],
                    })
                return "A solicitação exigiu consultas demais. Vamos dividir em etapas: o que você gostaria de verificar primeiro?"

            results_to_append: list[dict[str, Any]] = []
            policy_review_conflicts: list[dict[str, Any]] = []
            product_detail_result: dict[str, Any] | None = None
            for call in calls:
                tool_calls_used += 1
                result = self.registry.execute(
                    call.name,
                    call.arguments,
                    ToolContext(services=self.services, session=session),
                )
                function_result = {
                    "type": "function_result",
                    "name": call.name,
                    "call_id": call.call_id,
                    "result": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}],
                }
                results_to_append.append(function_result)

                # Product specifications are structured facts. When the model
                # requests only one product detail lookup, format those fields
                # deterministically rather than asking the LLM to reinterpret
                # keys such as `neck` or `scale`.
                if (
                    len(calls) == 1
                    and call.name == "get_product_details"
                    and isinstance(result, dict)
                    and result.get("ok") is True
                    and isinstance(result.get("data"), dict)
                ):
                    product_detail_result = result["data"]

                # Unresolved policy conflicts are a deterministic safety gate:
                # do not rely on the LLM to notice or correctly interpret them.
                if call.name == "search_store_policies" and isinstance(result, dict):
                    data = result.get("data")
                    if result.get("ok") is True and isinstance(data, dict):
                        if data.get("requires_human_review") is True:
                            conflicts = data.get("conflicts") or []
                            if isinstance(conflicts, list):
                                policy_review_conflicts.extend(
                                    item for item in conflicts if isinstance(item, dict)
                                )
                            if not conflicts:
                                policy_review_conflicts.append({"key": "unresolved_policy"})
            session.history.extend(results_to_append)
            if policy_review_conflicts:
                answer = self._format_policy_human_review(policy_review_conflicts)
                session.history.append({"type": "text", "text": answer})
                return answer
            if product_detail_result is not None:
                answer = self._format_product_details(product_detail_result)
                session.history.append({"type": "text", "text": answer})
                return answer

    @staticmethod
    def _format_product_details(data: dict[str, Any]) -> str:
        """Format catalog details from known fields without LLM reinterpretation."""
        name = str(data.get("name") or "Produto")
        product_id = data.get("product_id", "não informado")
        category = str(data.get("category") or "não informada")
        price = str(data.get("formatted_price") or "não informado")
        availability_value = str(data.get("availability") or "unknown").casefold()
        availability_labels = {
            "available": "Disponível",
            "out_of_stock": "Sem estoque",
            "coming_soon": "Em breve",
            "discontinued": "Descontinuado",
        }
        availability = availability_labels.get(availability_value, "Não confirmada")
        stock = data.get("stock_quantity")
        description = str(data.get("description") or "Sem descrição cadastrada.")
        status_value = str(data.get("status") or "unknown").casefold()
        status_labels = {
            "active": "Ativo",
            "discontinued": "Descontinuado",
            "coming_soon": "Em breve",
        }
        status = status_labels.get(status_value, "Não informado")

        spec_labels = {
            "top": "Tampo",
            "back_sides": "Fundo e laterais",
            "neck": "Braço",
            "strings": "Cordas",
            "scale": "Comprimento da escala",
            "electronics": "Sistema eletrônico",
            "color": "Cor/acabamento",
        }
        specs = data.get("specs")
        spec_lines: list[str] = []
        if isinstance(specs, dict):
            for key, value in specs.items():
                label = spec_labels.get(str(key), f"Campo cadastrado ({key})")
                rendered = str(value)
                if str(key) == "electronics":
                    rendered = {"no": "Não", "yes": "Sim"}.get(rendered.casefold(), rendered)
                spec_lines.append(f"- {label}: {rendered}")

        lines = [
            f"**{name}** (ID {product_id})",
            f"Categoria: {category}",
            f"Preço cadastrado: {price}",
            f"Disponibilidade: {availability}",
        ]
        if isinstance(stock, int):
            lines.append(f"Estoque cadastrado: {stock} unidade(s) (snapshot)")
        lines.extend([f"Status: {status}", f"Descrição: {description}"])
        if spec_lines:
            lines.append("**Especificações cadastradas**")
            lines.extend(spec_lines)

        promotion = data.get("promotion")
        if isinstance(promotion, dict):
            promotion_name = str(promotion.get("description") or "Promoção ativa")
            promotion_price = str(promotion.get("formatted_promotional_price") or "")
            discount = promotion.get("discount_percent")
            promotion_line = f"Promoção ativa: {promotion_name}"
            if discount is not None:
                promotion_line += f" ({discount}% de desconto)"
            if promotion_price:
                promotion_line += f" — preço promocional: {promotion_price}"
            lines.append(promotion_line)
        else:
            lines.append("Promoção ativa: nenhuma registrada para este produto.")

        lines.append("Os dados de preço e estoque refletem o snapshot do catálogo fornecido; não são uma consulta em tempo real.")
        return "\n".join(lines)

    @staticmethod
    def _format_policy_human_review(conflicts: list[dict[str, Any]]) -> str:
        """Return a safe, deterministic response for unresolved policy conflicts."""
        keys = {str(item.get("key", "")) for item in conflicts}
        if "warranty_after_30_days" in keys:
            return (
                "O manual apresenta duas orientações que precisam ser conciliadas: "
                "a seção 4.2 (página 4) menciona o acionamento do fabricante após "
                "30 dias, enquanto a seção 8.1 (página 7) prevê garantia legal de "
                "90 dias. O documento não esclarece como essas regras se aplicam "
                "em conjunto. Para não fornecer uma informação incorreta, não vou "
                "afirmar que a cobertura termina após 30 dias. A equipe da loja "
                "precisa confirmar o procedimento para o caso específico."
            )
        if "freight_exactly_500" in keys:
            return (
                "O manual informa frete grátis para compras acima de R$ 500,00 e "
                "taxa de R$ 35,00 para compras abaixo desse valor, mas não define "
                "o valor exato de R$ 500,00. A equipe da loja precisa confirmar "
                "essa condição antes de informar o frete."
            )
        if keys.intersection({"email_spelling", "whatsapp_number"}):
            return (
                "O manual apresenta informações divergentes sobre os canais de "
                "contato. Para evitar passar um endereço ou número incorreto, "
                "a equipe da loja precisa confirmar o contato oficial."
            )
        return (
            "Encontrei uma divergência ou informação não confirmada no manual da "
            "loja. Para não fornecer uma orientação incorreta, a equipe da loja "
            "precisa confirmar esse ponto antes de eu responder com segurança."
        )

    @staticmethod
    def _extract_calls(steps: list[dict[str, Any]]) -> list[ModelToolCall]:
        calls: list[ModelToolCall] = []
        for step in steps:
            if step.get("type") != "function_call":
                continue
            args = step.get("arguments") or {}
            calls.append(
                ModelToolCall(
                    call_id=str(step.get("id") or ""),
                    name=str(step.get("name") or ""),
                    arguments=args if isinstance(args, dict) else {},
                )
            )
        return calls

    def _handle_pending_order_verification(self, session: AgentSession, message: str) -> str:
        order_id = session.pending_order_id
        if order_id is None:
            return "Não há uma consulta de pedido aguardando verificação."
        if looks_like_cancel(message):
            session.pending_order_id = None
            return "Tudo bem, cancelei a consulta do pedido."

        digits = normalize_phone_input(message)
        if not 8 <= len(digits) <= 15:
            return "Não consegui validar o formato do telefone. Envie somente o telefone cadastrado no pedido ou escreva 'cancelar'."

        try:
            grant = self.services.identity.verify_order_access(
                order_id,
                SecretStr(message),
                session_id=session.session_id,
            )
            data = self.services.orders.get_order_status(
                order_id,
                authorization=grant,
                session_id=session.session_id,
            )
        except AuthenticationFailedError:
            remaining = self.services.identity.attempts_remaining(session.session_id)
            if remaining <= 0:
                session.pending_order_id = None
                return "Não foi possível confirmar os dados. Por segurança, a consulta foi bloqueada. Entre em contato com a equipe da loja pelos canais oficiais."
            return f"Não foi possível confirmar os dados. Confira o telefone cadastrado e tente novamente. Tentativas restantes: {remaining}."
        except AppError as exc:
            session.pending_order_id = None
            return exc.public_message
        except ValidationError:
            return "Não consegui validar esse telefone. Confira o número cadastrado e tente novamente."
        except Exception:
            session.pending_order_id = None
            return "Não consegui concluir a consulta do pedido. A equipe da loja precisa verificar o caso."

        session.pending_order_id = None
        return self._format_order_status(data)

    @staticmethod
    def _format_order_status(data: Any) -> str:
        status_labels = {
            "pending": "Pendente",
            "confirmed": "Confirmado",
            "shipped": "Enviado",
            "delivered": "Entregue",
            "cancelled": "Cancelado",
        }
        status_value = getattr(data.status, "value", str(data.status))
        lines = [
            f"Encontrei o pedido **#{data.order_id}**.",
            f"Status registrado: **{status_labels.get(status_value, status_value)}**.",
            f"Data do pedido: {data.order_date.strftime('%d/%m/%Y')}.",
        ]
        if data.items:
            lines.append("Itens: " + "; ".join(f"{item.quantity}x {item.product_name}" for item in data.items) + ".")
        if data.tracking_code:
            lines.append(f"Código de rastreio registrado: {data.tracking_code}.")
        if data.estimated_delivery:
            lines.append(f"Previsão registrada no conjunto de dados: {data.estimated_delivery.strftime('%d/%m/%Y')} (não é uma atualização em tempo real).")
        if data.dataset_is_static:
            reference = data.latest_order_date_in_dataset.strftime("%d/%m/%Y") if data.latest_order_date_in_dataset else "não informada"
            lines.append(f"Importante: consultei uma base estática, com pedidos até {reference}; o status pode ter mudado desde a última atualização.")
        return "\n".join(lines)
