from decimal import Decimal
from typing import Any


def require_positive_quantity(quantity: Any) -> Decimal:
    """
    Enforce an InvoiceItem's quantity is present and greater than zero.
    Mirrors apps.quotations.validators.require_positive_quantity exactly
    -- an invoice, like a quotation, is a client-facing commercial
    document.
    """
    if quantity is None:
        raise ValueError("quantity is required.")
    if Decimal(quantity) <= 0:
        raise ValueError("quantity must be greater than zero.")
    return quantity
