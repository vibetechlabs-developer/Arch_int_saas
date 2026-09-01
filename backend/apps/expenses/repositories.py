import uuid
from typing import Any, Dict, Optional

from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.company.models import Company
from apps.expenses.models import Expense

User = get_user_model()


class ExpenseRepository:
    """
    Data-access layer for Expense (BE-044). Mirrors
    apps.invoices.repositories.InvoiceRepository's shape.
    """

    @staticmethod
    def all_for_project(project_id: str | uuid.UUID) -> QuerySet[Expense]:
        return Expense.objects.select_related("company", "project", "employee", "added_by").filter(
            project_id=project_id
        )

    @staticmethod
    def get_by_id(expense_id: str | uuid.UUID) -> Expense:
        try:
            return Expense.objects.select_related("company", "project", "employee", "added_by").get(
                id=expense_id
            )
        except (Expense.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested expense was not found.")

    @staticmethod
    def create(**fields: Any) -> Expense:
        return Expense.objects.create(**fields)

    @staticmethod
    def save(expense: Expense, fields: Optional[Dict[str, Any]] = None) -> Expense:
        for field, value in (fields or {}).items():
            setattr(expense, field, value)
        expense.save()
        return expense

    @staticmethod
    def soft_delete(expense: Expense) -> None:
        expense.delete()

    @staticmethod
    def get_company_by_id(company_id: str | uuid.UUID) -> Company:
        try:
            return Company.objects.get(id=company_id)
        except (Company.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The specified company was not found.")

    @staticmethod
    def get_user_by_id(user_id: str | uuid.UUID) -> User:
        try:
            return User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The specified user was not found.")
