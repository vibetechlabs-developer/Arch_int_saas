import uuid
from typing import Any, Dict, Optional
from django.db.models import Q, QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.company.models import Company, get_default_company_settings


class CompanyService:
    """
    Business logic and orchestration service for Company tenants.
    Adheres to Folder_Structure.md §2: controllers contain no business logic;
    all data operations and validations run through CompanyService.
    """

    @classmethod
    def create_company(
        cls,
        name: str,
        currency: str = "INR",
        gst_number: Optional[str] = None,
        status: str = "trial",
        settings: Optional[Dict[str, Any]] = None,
    ) -> Company:
        """
        Create a new Company tenant.
        """
        company_settings = get_default_company_settings()
        if settings and isinstance(settings, dict):
            company_settings.update(settings)

        company = Company.objects.create(
            name=name.strip(),
            currency=currency.strip(),
            gst_number=gst_number.strip() if gst_number else None,
            status=status,
            settings=company_settings,
        )
        return company

    @classmethod
    def get_company_by_id(cls, company_id: str | uuid.UUID) -> Company:
        """
        Retrieve an active, non-deleted Company by primary key UUID.
        Raises NotFound if company does not exist or is soft-deleted.
        """
        try:
            return Company.objects.get(id=company_id)
        except (Company.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested company was not found.")

    @classmethod
    def list_companies(
        cls,
        status: Optional[str] = None,
        search: Optional[str] = None,
        ordering: str = "-created_at",
    ) -> QuerySet[Company]:
        """
        List active companies with optional status filtering and search.
        """
        queryset = Company.objects.all()

        if status:
            queryset = queryset.filter(status=status)

        if search:
            search_query = search.strip()
            queryset = queryset.filter(
                Q(name__icontains=search_query) | Q(gst_number__icontains=search_query)
            )

        valid_order_fields = {
            "created_at",
            "-created_at",
            "name",
            "-name",
            "status",
            "-status",
            "updated_at",
            "-updated_at",
        }
        if ordering in valid_order_fields:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        return queryset

    @classmethod
    def update_company(
        cls,
        company_id: str | uuid.UUID,
        validated_data: Dict[str, Any],
        is_platform_admin: bool = False,
    ) -> Company:
        """
        Update an existing Company tenant.
        Only Platform Admins are allowed to alter tenant status.
        """
        company = cls.get_company_by_id(company_id)

        if "name" in validated_data:
            company.name = validated_data["name"].strip()

        if "currency" in validated_data:
            company.currency = validated_data["currency"].strip()

        if "gst_number" in validated_data:
            company.gst_number = (
                validated_data["gst_number"].strip()
                if validated_data["gst_number"]
                else None
            )

        if "status" in validated_data and is_platform_admin:
            company.status = validated_data["status"]

        if "settings" in validated_data and isinstance(validated_data["settings"], dict):
            current_settings = dict(company.settings or {})
            current_settings.update(validated_data["settings"])
            company.settings = current_settings

        company.save()
        return company

    @classmethod
    def soft_delete_company(cls, company_id: str | uuid.UUID) -> None:
        """
        Soft-delete a Company tenant by setting deleted_at timestamp.
        """
        company = cls.get_company_by_id(company_id)
        company.delete()
