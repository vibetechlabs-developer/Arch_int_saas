from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from django import template

register = template.Library()


@register.filter(name="money")
def money(value: Any, currency: Optional[str] = None) -> str:
    """
    Formats an already backend-authoritative Decimal/decimal-string value
    as "1,234.56" (thousands separator, 2 decimal places), optionally
    prefixed with a real ISO currency code (e.g. "INR 1,234.56"). Never a
    hardcoded currency symbol -- PDF templates only ever format a number
    the view already computed; they never sum, subtract, or otherwise
    calculate a financial value themselves.
    """
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal("0.00")
    formatted = f"{amount:,.2f}"
    if currency:
        return f"{currency} {formatted}"
    return formatted
