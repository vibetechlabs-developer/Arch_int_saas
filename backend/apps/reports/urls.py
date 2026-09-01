from django.urls import re_path

from apps.reports.views import ExpenseReportView, FinanceReportView

urlpatterns = [
    re_path(r"^reports/finance/?$", FinanceReportView.as_view(), name="report-finance"),
    re_path(r"^reports/expenses/?$", ExpenseReportView.as_view(), name="report-expenses"),
]
