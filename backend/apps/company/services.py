import uuid
from typing import Any, Dict, Optional
from django.db.models import QuerySet

from apps.company import selectors, validators
from apps.company.models import Company
from apps.company.repositories import CompanyRepository


class CompanyService:
    """
    Business logic and orchestration service for Company tenants.
    Adheres to Folder_Structure.md §2: controllers contain no business logic;
    all data operations and validations run through CompanyService, which in
    turn delegates persistence to CompanyRepository, read/list queries to
    apps.company.selectors, and input normalization to apps.company.validators.
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
        fields = validators.build_create_fields(name, currency, gst_number, status, settings)
        return CompanyRepository.create(**fields)

    @classmethod
    def get_company_by_id(cls, company_id: str | uuid.UUID) -> Company:
        """
        Retrieve an active, non-deleted Company by primary key UUID.
        Raises NotFound if company does not exist or is soft-deleted.
        """
        return CompanyRepository.get_by_id(company_id)

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
        return selectors.list_companies(status=status, search=search, ordering=ordering)

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
        fields = validators.build_update_fields(
            validated_data, company.settings, is_platform_admin
        )
        return CompanyRepository.save(company, fields)

    @classmethod
    def soft_delete_company(cls, company_id: str | uuid.UUID) -> None:
        """
        Soft-delete a Company tenant by setting deleted_at timestamp.
        """
        company = cls.get_company_by_id(company_id)
        CompanyRepository.soft_delete(company)
