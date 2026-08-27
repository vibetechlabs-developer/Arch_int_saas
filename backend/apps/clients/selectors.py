from django.db.models import QuerySet

from apps.clients.models import Client
from apps.clients.repositories import ClientRepository

# Minimal foundation only — BE-022 has no list endpoint yet. Search/filter/
# ordering parameters are added in BE-023 alongside the list view, mirroring
# apps.company.selectors.list_companies / apps.users.selectors.list_roles.


def list_clients_for_company(company_id) -> QuerySet[Client]:
    """
    Tenant-scoped Client queryset, ordered newest-first. BE-023 will extend
    this with search/status filters and validated ordering, the same way
    CompanyService/RoleService's list selectors work today.
    """
    return ClientRepository.all().filter(company_id=company_id).order_by("-created_at")
