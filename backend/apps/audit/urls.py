from django.urls import re_path

from apps.audit.views import ActivityLogListView

urlpatterns = [
    re_path(r"^activity-logs/?$", ActivityLogListView.as_view(), name="activity-log-list"),
]
