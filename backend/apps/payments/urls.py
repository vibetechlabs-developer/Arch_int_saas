from django.urls import re_path

from apps.payments.views import (
    PaymentListCreateView,
    PaymentReceiptDownloadView,
    PaymentReceiptUploadView,
    PaymentVoidView,
)

urlpatterns = [
    re_path(
        r"^invoices/(?P<invoice_id>[0-9a-fA-F-]{36})/payments/?$",
        PaymentListCreateView.as_view(),
        name="payment-list",
    ),
    re_path(
        r"^payments/receipts/upload/?$",
        PaymentReceiptUploadView.as_view(),
        name="payment-receipt-upload",
    ),
    re_path(
        r"^payments/(?P<payment_id>[0-9a-fA-F-]{36})/receipt/?$",
        PaymentReceiptDownloadView.as_view(),
        name="payment-receipt-download",
    ),
    re_path(
        r"^payments/(?P<payment_id>[0-9a-fA-F-]{36})/?$",
        PaymentVoidView.as_view(),
        name="payment-void",
    ),
]
