# Generated for BE-012/BE-014 – Role Model

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("company", "0001_initial"),
        ("users", "0002_companymembership"),
    ]

    operations = [
        migrations.CreateModel(
            name="Role",
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
                    "name",
                    models.CharField(
                        help_text="Human-readable role name, unique per company.",
                        max_length=100,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Optional free-form description of the role's purpose.",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Indicates whether the role is currently usable.",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        help_text="The tenant company this role belongs to.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="roles",
                        to="company.company",
                    ),
                ),
            ],
            options={
                "verbose_name": "role",
                "verbose_name_plural": "roles",
                "db_table": "role",
                "ordering": ["-created_at"],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(deleted_at__isnull=True),
                        fields=("company", "name"),
                        name="unique_active_role_per_company",
                    )
                ],
            },
        ),
    ]
