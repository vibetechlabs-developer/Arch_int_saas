from django.contrib import admin
from apps.authentication.models import PasswordResetToken


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "expires_at", "consumed_at", "created_at")
    list_filter = ("created_at", "expires_at", "consumed_at")
    search_fields = ("user__email", "user__name")
    readonly_fields = ("id", "user", "token_hash", "expires_at", "consumed_at", "created_at", "updated_at")
    ordering = ("-created_at",)
