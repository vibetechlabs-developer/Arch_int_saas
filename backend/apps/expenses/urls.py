from django.urls import re_path

from apps.expenses.views import (
    ExpenseApproveView,
    ExpenseDetailView,
    ExpenseListCreateView,
    ExpenseMarkPaidView,
    ExpenseSubmitView,
)

urlpatterns = [
    re_path(
        r"^projects/(?P<project_id>[0-9a-fA-F-]{36})/expenses/?$",
        ExpenseListCreateView.as_view(),
        name="expense-list",
    ),
    re_path(
        r"^expenses/(?P<expense_id>[0-9a-fA-F-]{36})/?$",
        ExpenseDetailView.as_view(),
        name="expense-detail",
    ),
    re_path(
        r"^expenses/(?P<expense_id>[0-9a-fA-F-]{36})/submit/?$",
        ExpenseSubmitView.as_view(),
        name="expense-submit",
    ),
    re_path(
        r"^expenses/(?P<expense_id>[0-9a-fA-F-]{36})/approve/?$",
        ExpenseApproveView.as_view(),
        name="expense-approve",
    ),
    re_path(
        r"^expenses/(?P<expense_id>[0-9a-fA-F-]{36})/mark-paid/?$",
        ExpenseMarkPaidView.as_view(),
        name="expense-mark-paid",
    ),
]
