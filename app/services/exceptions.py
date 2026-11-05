"""Service-specific exceptions that extend the shared error contract."""

from app.domain.errors import AppError
from app.domain.schemas import ToolErrorCode


class ProductUnavailableError(AppError):
    """Raised when payment options are requested for a non-saleable product."""

    code: ToolErrorCode = "VALIDATION_ERROR"
    public_message = "Este produto não está disponível para compra no cadastro fornecido."


class InstallmentNotAllowedError(AppError):
    """Raised when a calculated installment is below the policy minimum."""

    code: ToolErrorCode = "VALIDATION_ERROR"
    public_message = (
        "O valor da compra não atende ao valor mínimo de parcela permitido "
        "para essa quantidade de vezes."
    )
