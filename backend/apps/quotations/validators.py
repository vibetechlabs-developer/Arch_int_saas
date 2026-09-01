from decimal import Decimal
from typing import Any


def require_positive_quantity(quantity: Any) -> Decimal:
    """
    Enforce a QuotationItem's quantity is present and greater than zero.
    Mirrors BOQItemService's inline "quantity is required" check (BE-036),
    extended with a positivity check since a quotation, unlike a BOQ draft,
    is a commercial document a client will see.
    """
    if quantity is None:
        raise ValueError("quantity is required.")
    if Decimal(quantity) <= 0:
        raise ValueError("quantity must be greater than zero.")
    return quantity
