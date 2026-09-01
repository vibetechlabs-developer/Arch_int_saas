from django.urls import re_path

from apps.invoices.views import (
    InvoiceCancelView,
    InvoiceDetailView,
    InvoiceListCreateView,
    InvoiceSendView,
)

urlpatterns = [
    re_path(
        r"^projects/(?P<project_id>[0-9a-fA-F-]{36})/invoices/?$",
        InvoiceListCreateView.as_view(),
        name="invoice-list",
    ),
    re_path(
        r"^invoices/(?P<invoice_id>[0-9a-fA-F-]{36})/?$",
        InvoiceDetailView.as_view(),
        name="invoice-detail",
    ),
    re_path(
        r"^invoices/(?P<invoice_id>[0-9a-fA-F-]{36})/send/?$",
        InvoiceSendView.as_view(),
        name="invoice-send",
    ),
    re_path(
        r"^invoices/(?P<invoice_id>[0-9a-fA-F-]{36})/cancel/?$",
        InvoiceCancelView.as_view(),
        name="invoice-cancel",
    ),
]
