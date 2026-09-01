from decimal import Decimal
from typing import Any


def require_positive_amount(amount: Any) -> Decimal:
    """
    Enforce an Expense's amount is present and greater than zero. Mirrors
    apps.payments.validators.require_positive_amount.
    """
    if amount is None:
        raise ValueError("amount is required.")
    if Decimal(amount) <= 0:
        raise ValueError("amount must be greater than zero.")
    return amount
