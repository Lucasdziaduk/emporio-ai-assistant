"""Money conversion and formatting helpers (integer cents internally)."""

from decimal import Decimal, InvalidOperation


def reais_to_cents(value: Decimal | str | int) -> int:
    """Convert a BRL amount to integer cents without binary floats."""
    if isinstance(value, bool):
        raise TypeError("Boolean values are not valid monetary amounts.")
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError) as exc:
        raise ValueError("Invalid monetary amount.") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("Monetary amount must be finite and non-negative.")
    cents = amount * Decimal("100")
    if cents != cents.to_integral_value():
        raise ValueError("Monetary amount cannot have more than two decimal places.")
    return int(cents)


def cents_to_brl(cents: int) -> str:
    """Format integer cents as Brazilian currency."""
    if isinstance(cents, bool) or not isinstance(cents, int):
        raise TypeError("Amount must be an integer number of cents.")
    if cents < 0:
        raise ValueError("Amount cannot be negative.")
    whole, fractional = divmod(cents, 100)
    formatted_whole = f"{whole:,}".replace(",", ".")
    return f"R$ {formatted_whole},{fractional:02d}"
