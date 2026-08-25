from django.urls import re_path

from apps.authentication.views import (
    ForgotPasswordView,
    LoginView,
    LogoutView,
    MeView,
    PlatformLoginView,
    ResetPasswordView,
    TokenRefreshView,
)

urlpatterns = [
    # Company user authentication endpoints
    re_path(r"^auth/login/?$", LoginView.as_view(), name="auth-login"),
    re_path(r"^auth/refresh/?$", TokenRefreshView.as_view(), name="auth-refresh"),
    re_path(r"^auth/logout/?$", LogoutView.as_view(), name="auth-logout"),
    re_path(r"^auth/me/?$", MeView.as_view(), name="auth-me"),
    re_path(
        r"^auth/forgot-password/?$",
        ForgotPasswordView.as_view(),
        name="auth-forgot-password",
    ),
    re_path(
        r"^auth/reset-password/?$",
        ResetPasswordView.as_view(),
        name="auth-reset-password",
    ),
    # Platform super admin authentication endpoint
    re_path(
        r"^platform-auth/login/?$",
        PlatformLoginView.as_view(),
        name="platform-auth-login",
    ),
]
