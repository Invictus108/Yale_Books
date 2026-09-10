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
            "FRONTEND_URL": "https://yalebooks-be079.web.app/",
            "ORIGIN": "https://yale-books.onrender.com/",
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

    def test_frontend_cors(self):
        origin = "https://yalebooks-be079.web.app"
        response = self.client.get("/api/me", headers={"Origin": origin})
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], origin)
        self.assertEqual(response.headers["Access-Control-Allow-Credentials"], "true")
        response = self.client.get("/api/me", headers={"Origin": "https://example.com"})
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    def test_production_auth_urls_and_cookies(self):
        self.assertEqual(self.module.SERVICE_URL, "https://yale-books.onrender.com/login_callback")
        self.assertEqual(self.client.get("/logout").location, "https://yalebooks-be079.web.app/")
        self.assertTrue(self.module.app.config["SESSION_COOKIE_SECURE"])
        self.assertEqual(self.module.app.config["SESSION_COOKIE_SAMESITE"], "None")


if __name__ == "__main__":
    unittest.main()
