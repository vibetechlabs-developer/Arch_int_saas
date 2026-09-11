import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

BACKEND_DIR = Path(__file__).resolve().parents[3]
INSECURE_DEFAULT_SECRET_KEY = (
    "django-insecure-fv5f2u((b)d0rj8z#hrnikk2vcg!w6c%mc7521c^s_4thv1gxg"
)


def _load_settings_in_subprocess(env_overrides: dict, print_expr: str = "") -> subprocess.CompletedProcess:
    """
    settings.py's DEBUG/SECRET_KEY guard (Part 7) and its DEBUG-dependent
    DEFAULT_RENDERER_CLASSES (Part 12) are both evaluated once, at module
    import time — they can't be flipped at runtime in the already-running
    test process (DEBUG is fixed for the whole pytest run). A real
    subprocess with controlled environment variables is the only way to
    exercise both branches of either guard.
    """
    script = (
        "import django, os; "
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); "
        "django.setup(); "
    )
    if print_expr:
        script += f"from django.conf import settings; print({print_expr})"

    env = os.environ.copy()
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


class SecretKeyHardeningTestCase(SimpleTestCase):
    """BE-021 master task Part 7."""

    def test_debug_false_with_insecure_default_secret_key_refuses_to_start(self):
        result = _load_settings_in_subprocess(
            {"DJANGO_DEBUG": "false", "DJANGO_SECRET_KEY": INSECURE_DEFAULT_SECRET_KEY}
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ImproperlyConfigured", result.stderr)

    def test_debug_false_with_a_real_secret_key_starts_fine(self):
        result = _load_settings_in_subprocess(
            {"DJANGO_DEBUG": "false", "DJANGO_SECRET_KEY": "a-real-unique-production-secret-key"}
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_debug_true_with_insecure_default_secret_key_still_works(self):
        """
        Local development must be unaffected — DEBUG=True keeps working
        with the checked-in insecure default, exactly as before this
        hardening was added.
        """
        result = _load_settings_in_subprocess(
            {"DJANGO_DEBUG": "true", "DJANGO_SECRET_KEY": INSECURE_DEFAULT_SECRET_KEY}
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class CsrfTrustedOriginsTestCase(SimpleTestCase):
    """BE-077 Part A: DJANGO_CSRF_TRUSTED_ORIGINS is environment-driven,
    never a wildcard, and never breaks local development."""

    def test_debug_development_configuration_still_boots(self):
        result = _load_settings_in_subprocess(
            {"DJANGO_DEBUG": "true", "DJANGO_SECRET_KEY": INSECURE_DEFAULT_SECRET_KEY}
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unset_defaults_to_empty_list_never_a_wildcard(self):
        env_overrides = {"DJANGO_DEBUG": "true", "DJANGO_SECRET_KEY": INSECURE_DEFAULT_SECRET_KEY}
        env_overrides.pop("DJANGO_CSRF_TRUSTED_ORIGINS", None)
        result = _load_settings_in_subprocess(
            env_overrides, print_expr="settings.CSRF_TRUSTED_ORIGINS"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "[]")
        self.assertNotIn("*", result.stdout)

    def test_single_production_style_origin_parses_correctly(self):
        result = _load_settings_in_subprocess(
            {
                "DJANGO_DEBUG": "false",
                "DJANGO_SECRET_KEY": "a-real-unique-production-secret-key",
                "DJANGO_CSRF_TRUSTED_ORIGINS": "https://example.test",
            },
            print_expr="settings.CSRF_TRUSTED_ORIGINS",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "['https://example.test']")

    def test_multiple_origins_parse_correctly(self):
        result = _load_settings_in_subprocess(
            {
                "DJANGO_DEBUG": "false",
                "DJANGO_SECRET_KEY": "a-real-unique-production-secret-key",
                "DJANGO_CSRF_TRUSTED_ORIGINS": "https://app.example.test,https://api.example.test",
            },
            print_expr="settings.CSRF_TRUSTED_ORIGINS",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(), "['https://app.example.test', 'https://api.example.test']"
        )

    def test_production_style_settings_boot_with_csrf_configured(self):
        """
        Full production-shaped env (DEBUG=false, real secret key, real CSRF
        origin) boots cleanly end to end -- not just the CSRF setting in
        isolation.
        """
        result = _load_settings_in_subprocess(
            {
                "DJANGO_DEBUG": "false",
                "DJANGO_SECRET_KEY": "a-real-unique-production-secret-key",
                "DJANGO_CSRF_TRUSTED_ORIGINS": "https://example.test",
                "DJANGO_SECURE_SSL_REDIRECT": "true",
            }
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class StorageBackendHardeningTestCase(SimpleTestCase):
    """
    BE-078: STORAGE_BACKEND selects the object-storage backend
    (config/settings.py's STORAGES dict). DEBUG/SECRET_KEY-style subprocess
    isolation isn't strictly required here (STORAGE_BACKEND doesn't branch
    on DEBUG), but the required-env-var validation raises at import time --
    exactly like the SECRET_KEY guard -- so the same subprocess pattern
    applies.
    """

    def test_unset_defaults_to_local_filesystem_storage(self):
        result = _load_settings_in_subprocess({}, print_expr="settings.STORAGES['default']['BACKEND']")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("FileSystemStorage", result.stdout)

    def test_local_mode_needs_no_aws_credentials(self):
        result = _load_settings_in_subprocess({"STORAGE_BACKEND": "local"})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_s3_mode_missing_all_credentials_refuses_to_start(self):
        result = _load_settings_in_subprocess({"STORAGE_BACKEND": "s3"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ImproperlyConfigured", result.stderr)
        self.assertIn("AWS_STORAGE_BUCKET_NAME", result.stderr)

    def test_s3_mode_missing_one_credential_refuses_to_start(self):
        result = _load_settings_in_subprocess(
            {
                "STORAGE_BACKEND": "s3",
                "AWS_STORAGE_BUCKET_NAME": "test-bucket",
                "AWS_ACCESS_KEY_ID": "fake-key",
                "AWS_SECRET_ACCESS_KEY": "fake-secret",
                # AWS_S3_REGION_NAME deliberately omitted
            }
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AWS_S3_REGION_NAME", result.stderr)

    def test_s3_mode_with_full_config_boots_and_configures_public_and_private_backends(self):
        result = _load_settings_in_subprocess(
            {
                "STORAGE_BACKEND": "s3",
                "AWS_STORAGE_BUCKET_NAME": "test-bucket",
                "AWS_ACCESS_KEY_ID": "fake-key",
                "AWS_SECRET_ACCESS_KEY": "fake-secret",
                "AWS_S3_REGION_NAME": "us-east-1",
            },
            print_expr=(
                "(settings.STORAGES['default']['OPTIONS']['default_acl'], "
                "settings.STORAGES['default']['OPTIONS']['querystring_auth'], "
                "settings.STORAGES['private']['OPTIONS']['default_acl'], "
                "settings.STORAGES['private']['OPTIONS']['querystring_auth'])"
            ),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # default (PUBLIC) -> public-read, permanent (unsigned) URLs.
        # private (PRIVATE) -> private ACL, always signed URLs.
        self.assertIn("('public-read', False, 'private', True)", result.stdout)

    def test_never_silently_falls_back_to_local_when_s3_explicitly_selected(self):
        """
        §22's explicit requirement: a deployment that selected S3 and is
        missing config must fail loudly, never silently serve from local
        disk instead.
        """
        result = _load_settings_in_subprocess({"STORAGE_BACKEND": "s3"})
        self.assertNotIn("FileSystemStorage", result.stdout)
        self.assertNotEqual(result.returncode, 0)


class BrowsableApiRendererHardeningTestCase(SimpleTestCase):
    """BE-021 master task Part 12."""

    def test_debug_true_includes_browsable_api_renderer(self):
        result = _load_settings_in_subprocess(
            {"DJANGO_DEBUG": "true", "DJANGO_SECRET_KEY": INSECURE_DEFAULT_SECRET_KEY},
            print_expr="settings.REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES']",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("BrowsableAPIRenderer", result.stdout)

    def test_debug_false_excludes_browsable_api_renderer(self):
        result = _load_settings_in_subprocess(
            {"DJANGO_DEBUG": "false", "DJANGO_SECRET_KEY": "a-real-unique-production-secret-key"},
            print_expr="settings.REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES']",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("BrowsableAPIRenderer", result.stdout)
        self.assertIn("JSONRenderer", result.stdout)
