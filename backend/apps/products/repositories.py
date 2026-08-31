import uuid
from typing import Any, Dict, Optional

from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.company.models import Company
from apps.products.models import ProductCategory


class ProductCategoryRepository:
    """
    Data-access layer for ProductCategory. Mirrors
    apps.clients.repositories.ClientRepository exactly (BACKEND_RULES.md:
    View -> Serializer -> Service -> Repository -> Model).
    """

    @staticmethod
    def all() -> QuerySet[ProductCategory]:
        return ProductCategory.objects.select_related("company").all()

    @staticmethod
    def get_by_id(category_id: str | uuid.UUID) -> ProductCategory:
        try:
            return ProductCategory.objects.select_related("company").get(id=category_id)
        except (ProductCategory.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested product category was not found.")

    @staticmethod
    def create(**fields: Any) -> ProductCategory:
        return ProductCategory.objects.create(**fields)

    @staticmethod
    def save(
        category: ProductCategory, fields: Optional[Dict[str, Any]] = None
    ) -> ProductCategory:
        for field, value in (fields or {}).items():
            setattr(category, field, value)
        category.save()
        return category

    @staticmethod
    def soft_delete(category: ProductCategory) -> None:
        category.delete()

    @staticmethod
    def get_company_by_id(company_id: str | uuid.UUID) -> Company:
        try:
            return Company.objects.get(id=company_id)
        except (Company.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The specified company was not found.")
