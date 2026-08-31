import uuid
from typing import Any, Dict, Optional

from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.company.models import Company
from apps.products.models import Product, ProductCategory, ProductSubcategory


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


class ProductSubcategoryRepository:
    """
    Data-access layer for ProductSubcategory (BE-032). Mirrors
    ProductCategoryRepository's shape exactly.
    """

    @staticmethod
    def all() -> QuerySet[ProductSubcategory]:
        return ProductSubcategory.objects.select_related("company", "category").all()

    @staticmethod
    def get_by_id(subcategory_id: str | uuid.UUID) -> ProductSubcategory:
        try:
            return ProductSubcategory.objects.select_related("company", "category").get(
                id=subcategory_id
            )
        except (ProductSubcategory.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested product subcategory was not found.")

    @staticmethod
    def create(**fields: Any) -> ProductSubcategory:
        return ProductSubcategory.objects.create(**fields)

    @staticmethod
    def save(
        subcategory: ProductSubcategory, fields: Optional[Dict[str, Any]] = None
    ) -> ProductSubcategory:
        for field, value in (fields or {}).items():
            setattr(subcategory, field, value)
        subcategory.save()
        return subcategory

    @staticmethod
    def soft_delete(subcategory: ProductSubcategory) -> None:
        subcategory.delete()


class ProductRepository:
    """
    Data-access layer for Product (BE-033). Mirrors
    ProductCategoryRepository/ProductSubcategoryRepository's shape exactly.
    """

    @staticmethod
    def all() -> QuerySet[Product]:
        return Product.objects.select_related("company", "subcategory", "subcategory__category").all()

    @staticmethod
    def get_by_id(product_id: str | uuid.UUID) -> Product:
        try:
            return Product.objects.select_related(
                "company", "subcategory", "subcategory__category"
            ).get(id=product_id)
        except (Product.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested product was not found.")

    @staticmethod
    def create(**fields: Any) -> Product:
        return Product.objects.create(**fields)

    @staticmethod
    def save(product: Product, fields: Optional[Dict[str, Any]] = None) -> Product:
        for field, value in (fields or {}).items():
            setattr(product, field, value)
        product.save()
        return product

    @staticmethod
    def soft_delete(product: Product) -> None:
        product.delete()

    @staticmethod
    def get_company_by_id(company_id: str | uuid.UUID) -> Company:
        try:
            return Company.objects.get(id=company_id)
        except (Company.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The specified company was not found.")
