"""Offline startup checks: no production database or model download is used."""
import os
import sys
import unittest
from unittest.mock import patch

from flask_sqlalchemy import SQLAlchemy


class DeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict(os.environ, {
            "DATABASE_URL": "sqlite:///:memory:",
            "SESSION_SECRET": "test-only-secret",
            "ORIGIN": "https://books.example.edu/",
        }), patch.object(SQLAlchemy, "create_all"):
            import app
        cls.module = app
        cls.client = app.app.test_client()

    def test_startup_does_not_import_ml_stack(self):
        self.assertNotIn("sentence_transformers", sys.modules)

    def test_health(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})

    def test_same_origin_needs_no_cors(self):
        # Frontend and API share an origin, so no allow-origin header is handed out.
        response = self.client.get("/api/me", headers={"Origin": "https://example.com"})
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)
        self.assertEqual(self.module.ALLOWED_ORIGINS, [])

    def test_production_auth_urls_and_cookies(self):
        self.assertEqual(self.module.SERVICE_URL, "https://books.example.edu/login_callback")
        # Relative redirect: cannot silently point at a dev host.
        self.assertEqual(self.client.get("/logout").location, "/")
        self.assertTrue(self.module.app.config["SESSION_COOKIE_SECURE"])
        # First-party cookie, so Lax survives third-party cookie blocking.
        self.assertEqual(self.module.app.config["SESSION_COOKIE_SAMESITE"], "Lax")

    def test_spa_routes_do_not_shadow_api(self):
        # Backend rules must still win over the <path:> catch-all.
        for route in ("/healthz", "/api/me"):
            self.assertEqual(self.client.get(route).status_code, 200, route)
        self.assertEqual(self.client.get("/login").status_code, 302)

    def test_frontend_served_from_dist(self):
        self.assertTrue(self.module.FRONTEND_DIST.replace("\\", "/").endswith("frontend/dist"))


if __name__ == "__main__":
    unittest.main()
