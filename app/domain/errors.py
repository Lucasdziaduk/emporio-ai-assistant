
"""Standardized application exceptions."""

from app.domain.schemas import ToolError, ToolErrorCode


class AppError(Exception):
    """Base exception for expected application errors."""

    code: ToolErrorCode = "INTERNAL_ERROR"

    public_message: str = (
        "Ocorreu um erro interno ao processar a solicitação."
    )

    def __init__(self) -> None:
        super().__init__(self.public_message)

    def to_tool_error(self) -> ToolError:
        """Convert the exception into a safe tool error."""

        return ToolError(
            code=self.code,
            message=self.public_message,
        )


class InvalidInputError(AppError):
    """Raised when input parameters are invalid."""

    code: ToolErrorCode = "VALIDATION_ERROR"

    public_message = (
        "Os parâmetros informados são inválidos."
    )


class NotFoundError(AppError):
    """Raised when a requested record does not exist."""

    code: ToolErrorCode = "NOT_FOUND"

    public_message = (
        "Não encontrei o registro solicitado "
        "nos dados disponíveis."
    )


class AmbiguousResultError(AppError):
    """Raised when multiple records match a query."""

    code: ToolErrorCode = "AMBIGUOUS_RESULT"

    public_message = (
        "Encontrei mais de uma correspondência. "
        "Preciso que você especifique melhor."
    )


class AuthenticationRequiredError(AppError):
    """Raised when identity verification is required."""

    code: ToolErrorCode = "AUTH_REQUIRED"

    public_message = (
        "É necessário verificar os dados do pedido "
        "antes de consultar suas informações."
    )


class AuthenticationFailedError(AppError):
    """Raised when customer verification fails."""

    code: ToolErrorCode = "AUTH_FAILED"

    public_message = (
        "Não foi possível confirmar os dados informados."
    )


class PolicyConflictError(AppError):
    """Raised when store policies contain conflicting rules."""

    code: ToolErrorCode = "POLICY_CONFLICT"

    public_message = (
        "As informações da política apresentam uma "
        "divergência que exige confirmação da equipe."
    )


class InsufficientEvidenceError(AppError):
    """Raised when retrieved evidence is insufficient."""

    code: ToolErrorCode = "INSUFFICIENT_EVIDENCE"

    public_message = (
        "Não encontrei evidências suficientes no manual "
        "para responder com segurança."
    )


class SourceUnavailableError(AppError):
    """Raised when a required data source is unavailable."""

    code: ToolErrorCode = "SOURCE_UNAVAILABLE"

    public_message = (
        "A fonte de dados não está disponível no momento."
    )


class InternalAppError(AppError):
    """Raised for unexpected internal application failures."""

    code: ToolErrorCode = "INTERNAL_ERROR"

    public_message = (
        "Ocorreu um erro interno ao processar a solicitação."
    )


def exception_to_tool_error(
    error: Exception,
) -> ToolError:
    """
    Convert an exception into a safe error for the LLM.

    Unexpected exceptions never expose their original
    messages or internal implementation details.
    """

    if isinstance(error, AppError):
        return error.to_tool_error()

    return ToolError(
        code="INTERNAL_ERROR",
        message=(
            "Ocorreu um erro interno ao processar a solicitação."
        ),
    )
