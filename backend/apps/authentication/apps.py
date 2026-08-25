from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.authentication"
    verbose_name = "Authentication"

    def ready(self):
        from apps.authentication import schema  # noqa: F401 — registers TenantJWTAuthenticationScheme with drf-spectacular
