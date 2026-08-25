# Generated for BE-011

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("company", "0001_initial"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyMembership",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "deleted_at",
                    models.DateTimeField(
                        blank=True,
                        db_index=True,
                        default=None,
                        editable=False,
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("invited", "Invited"),
                            ("revoked", "Revoked"),
                        ],
                        db_index=True,
                        default="active",
                        help_text="Status of the user membership in this company.",
                        max_length=50,
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        help_text="The tenant company this membership belongs to.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="company.company",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="The user assigned to this company membership.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "company membership",
                "verbose_name_plural": "company memberships",
                "db_table": "company_membership",
                "ordering": ["-created_at"],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(deleted_at__isnull=True),
                        fields=("company", "user"),
                        name="unique_active_company_user_membership",
                    )
                ],
            },
        ),
    ]
