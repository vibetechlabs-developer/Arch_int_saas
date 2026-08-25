from typing import Optional

from django.db.models import Q
from rest_framework import exceptions as drf_exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.authentication.tokens import CompanyUserAccessToken, PlatformAdminAccessToken
from apps.users.models import CompanyMembership, CompanyMembershipStatus, User


class TenantJWTAuthentication(JWTAuthentication):
    """Custom JWT authentication that resolves tenant (company) information.

    After the standard JWTAuthentication has validated the token and set ``request.user``
    and ``request.auth``, this class attaches ``request.company_id`` (the UUID/id of the
    tenant company) and ``request.is_platform_admin`` (bool) to the request object.

    For regular company users, the tenant is derived from an active ``CompanyMembership``
    linking the authenticated user to a ``Company``. If the user belongs to multiple
    companies, a ``company_id`` must be supplied via request query parameters ``companyId``
    or ``company_id`` or via request data for non‑GET methods. The supplied ``company_id``
    is validated against the user's active memberships.
    """

    def authenticate(self, request):
        # Perform the standard JWT authentication first.
        auth_result = super().authenticate(request)
        if auth_result is None:
            return None
        user, token = auth_result
        # Determine platform admin flag from the SimpleJWT-native `token_type`
        # claim (set unconditionally by CompanyUserAccessToken/PlatformAdminAccessToken
        # and validated by SimpleJWT's own verify_token_type() before we get here).
        # This must match apps.users.permissions.is_platform_admin(), which uses the
        # same claim — the redundant custom `user_type` claim is not guaranteed to be
        # present depending on how the token was minted (e.g. AccessToken.for_user()
        # called directly, bypassing the RefreshToken.for_user() overrides that set it).
        token_type = token.get("token_type", None) if hasattr(token, "get") else token.payload.get("token_type", None)
        request.is_platform_admin = token_type == "platform_admin"
        # Certain auth endpoints do not require tenant resolution.
        exempt_paths = ["/auth/logout", "/auth/me", "/auth/refresh"]
        if request.path in exempt_paths:
            request.company_id = None
            return (user, token)
        # Resolve tenant for regular company users.
        if not request.is_platform_admin:
            # Extract supplied company ID from query params or request body.
            supplied_company_id = (
                request.query_params.get("companyId")
                or request.query_params.get("company_id")
                or getattr(request, "data", {}).get("company_id")
                or getattr(request, "data", {}).get("companyId")
            )
            # Query active memberships for the user.
            active_memberships = CompanyMembership.objects.filter(
                user=user,
                status=CompanyMembershipStatus.ACTIVE,
                deleted_at__isnull=True,
            )
            if supplied_company_id:
                # Validate that the supplied company belongs to an active membership.
                if active_memberships.filter(company_id=supplied_company_id).exists():
                    request.company_id = supplied_company_id
                else:
                    # Supplied company is invalid, unauthorized, inactive, or soft‑deleted.
                    raise drf_exceptions.PermissionDenied("Invalid or unauthorized companyId supplied.")
            else:
                # No companyId supplied; resolve based on active memberships.
                count = active_memberships.count()
                if count == 1:
                    request.company_id = active_memberships.first().company_id
                elif count > 1:
                    # Ambiguous tenant – multiple active memberships without explicit company.
                    raise drf_exceptions.PermissionDenied("Multiple active company memberships found; specify companyId.")
                else:
                    # Authenticated with a valid token, but not authorized for any
                    # company — this is a permission gap, not an authentication
                    # failure (Error_Handling.md §PermissionError), so 403 not 401.
                    raise drf_exceptions.PermissionDenied("User has no active company membership.")
        else:
            request.company_id = None
        # Return the original (user, token) tuple.
        return (user, token)
