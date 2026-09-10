from django.urls import re_path

from apps.quotations.views import (
    QuotationApproveView,
    QuotationDetailView,
    QuotationListCreateView,
    QuotationPdfView,
    QuotationRejectView,
    QuotationReviseView,
    QuotationSendView,
)

urlpatterns = [
    re_path(
        r"^projects/(?P<project_id>[0-9a-fA-F-]{36})/quotations/?$",
        QuotationListCreateView.as_view(),
        name="quotation-list",
    ),
    re_path(
        r"^quotations/(?P<quotation_id>[0-9a-fA-F-]{36})/?$",
        QuotationDetailView.as_view(),
        name="quotation-detail",
    ),
    re_path(
        r"^quotations/(?P<quotation_id>[0-9a-fA-F-]{36})/revise/?$",
        QuotationReviseView.as_view(),
        name="quotation-revise",
    ),
    re_path(
        r"^quotations/(?P<quotation_id>[0-9a-fA-F-]{36})/pdf/?$",
        QuotationPdfView.as_view(),
        name="quotation-pdf",
    ),
    re_path(
        r"^quotations/(?P<quotation_id>[0-9a-fA-F-]{36})/send/?$",
        QuotationSendView.as_view(),
        name="quotation-send",
    ),
    re_path(
        r"^quotations/(?P<quotation_id>[0-9a-fA-F-]{36})/approve/?$",
        QuotationApproveView.as_view(),
        name="quotation-approve",
    ),
    re_path(
        r"^quotations/(?P<quotation_id>[0-9a-fA-F-]{36})/reject/?$",
        QuotationRejectView.as_view(),
        name="quotation-reject",
    ),
]
