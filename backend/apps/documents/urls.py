from django.urls import re_path

from apps.documents.views import (
    DocumentDetailView,
    DocumentDownloadView,
    DocumentListCreateView,
    DocumentUploadView,
)

urlpatterns = [
    re_path(
        r"^projects/(?P<project_id>[0-9a-fA-F-]{36})/documents/?$",
        DocumentListCreateView.as_view(),
        name="document-list",
    ),
    re_path(
        r"^documents/upload/?$",
        DocumentUploadView.as_view(),
        name="document-upload",
    ),
    re_path(
        r"^documents/(?P<document_id>[0-9a-fA-F-]{36})/download/?$",
        DocumentDownloadView.as_view(),
        name="document-download",
    ),
    re_path(
        r"^documents/(?P<document_id>[0-9a-fA-F-]{36})/?$",
        DocumentDetailView.as_view(),
        name="document-detail",
    ),
]
