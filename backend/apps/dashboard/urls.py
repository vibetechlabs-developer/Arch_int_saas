from django.urls import re_path

from apps.dashboard.views import DashboardView

urlpatterns = [
    re_path(r"^reports/dashboard/?$", DashboardView.as_view(), name="dashboard"),
]
