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
