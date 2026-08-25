import yaml
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken

User = get_user_model()


class ApiDocsTestCase(TestCase):
    """
    BE-016: OpenAPI schema + interactive docs endpoints.
    Covers the routes wired in config/urls.py — /schema/, /docs/, /redoc/.
    """

    def setUp(self):
        self.client = APIClient()

    def test_schema_endpoint_public_and_valid(self):
        """
        GET /schema/ is reachable without authentication and returns a
        parseable OpenAPI document naming this project.
        """
        response = self.client.get("/schema/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("openapi", response["Content-Type"])

        schema = yaml.safe_load(response.content)
        self.assertEqual(schema["openapi"], "3.0.3")
        self.assertEqual(schema["info"]["title"], "INT Projects SaaS API")

    def test_schema_declares_tenant_jwt_security_scheme(self):
        """
        The TenantJWTAuthentication OpenApiAuthenticationExtension (BE-016)
        must register a Bearer/JWT security scheme, or every authenticated
        endpoint in the generated docs is left with an unresolved auth type.
        """
        response = self.client.get("/schema/")
        schema = yaml.safe_load(response.content)

        security_schemes = schema["components"]["securitySchemes"]
        self.assertIn("TenantJWTAuth", security_schemes)
        self.assertEqual(security_schemes["TenantJWTAuth"]["type"], "http")
        self.assertEqual(security_schemes["TenantJWTAuth"]["scheme"], "bearer")
        self.assertEqual(security_schemes["TenantJWTAuth"]["bearerFormat"], "JWT")

    def test_schema_includes_known_endpoints(self):
        """
        Sanity check that CompanyViewSet/RoleViewSet (previously unresolved
        due to a missing `queryset` attribute) now resolve cleanly into the
        generated schema alongside the authentication endpoints.
        """
        response = self.client.get("/schema/")
        schema = yaml.safe_load(response.content)
        paths = schema["paths"]

        for expected_path in [
            "/auth/login/",
            "/auth/me/",
            "/companies/",
            "/roles/",
        ]:
            self.assertIn(expected_path, paths)

    def test_swagger_ui_public_and_renders(self):
        """
        GET /docs/ (Swagger UI) is reachable without authentication.
        """
        response = self.client.get("/docs/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"swagger-ui", response.content.lower())

    def test_redoc_public_and_renders(self):
        """
        GET /redoc/ (ReDoc) is reachable without authentication.
        """
        response = self.client.get("/redoc/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"redoc", response.content.lower())

    def test_docs_accessible_with_token_and_no_company_membership(self):
        """
        TenantJWTAuthentication.authenticate() runs on every request
        regardless of a view's permission_classes (DRF's APIView.initial()
        always calls perform_authentication()). A caller with a stored
        Bearer token but zero active company memberships would normally get
        403 PermissionDenied from tenant resolution — /schema/, /docs/, and
        /redoc/ must be exempt from that check so simply having the docs
        open in a browser tab with a token present never errors.
        """
        user = User.objects.create_user(
            email="docs-viewer@example.com",
            name="Docs Viewer",
            password="StrongPassword123!",
        )
        token = str(CompanyUserAccessToken.for_user(user))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        for path in ["/schema/", "/docs/", "/redoc/"]:
            response = self.client.get(path)
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                msg=f"{path} should be reachable even with a token from a user with no company membership",
            )
