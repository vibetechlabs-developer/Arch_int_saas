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
