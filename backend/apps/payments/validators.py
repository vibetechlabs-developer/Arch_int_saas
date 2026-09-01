from decimal import Decimal
from typing import Any


def require_positive_amount(amount: Any) -> Decimal:
    """
    Enforce a Payment's amount is present and greater than zero. Mirrors
    apps.quotations.validators.require_positive_quantity's shape.
    """
    if amount is None:
        raise ValueError("amount is required.")
    if Decimal(amount) <= 0:
        raise ValueError("amount must be greater than zero.")
    return amount
