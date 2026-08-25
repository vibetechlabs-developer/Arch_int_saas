from drf_spectacular.extensions import OpenApiAuthenticationExtension


class TenantJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """
    Registers apps.authentication.authentication.TenantJWTAuthentication with
    drf-spectacular (BE-016) so generated docs show the correct Bearer/JWT
    security scheme instead of leaving every authenticated endpoint unresolved.

    target_class is given as a dotted string, per drf-spectacular convention,
    so this module never has to import apps.authentication.authentication
    directly (avoids import-order coupling at app-loading time).
    """

    target_class = "apps.authentication.authentication.TenantJWTAuthentication"
    name = "TenantJWTAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Bearer JWT issued by POST /auth/login or POST /platform-auth/login. "
                "Company-user tokens resolve tenant scope server-side from the "
                "caller's active CompanyMembership records (never from a "
                "client-supplied company ID); platform-admin tokens bypass tenant "
                "resolution. See 05_Security/Tenant.md."
            ),
        }
