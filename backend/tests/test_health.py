from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings


def test_health_ok():
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json().get("status") == "ok"


def test_login_cookie_flags_prod():
    prev_env = settings.environment
    prev_backend = settings.backend_url
    prev_frontend = settings.frontend_url
    settings.environment = "prod"
    settings.backend_url = "https://wishshare.onrender.com"
    settings.frontend_url = "https://wishshare.vercel.app"
    try:
        client = TestClient(app)
        email = f"user-{uuid4().hex}@example.com"
        password = "Test1234!"
        client.post(
            "/auth/register",
            json={"email": email, "password": password, "name": "User"},
        )
        res = client.post("/auth/login", json={"email": email, "password": password})
        set_cookie = res.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Secure" in set_cookie
        assert "SameSite=None" in set_cookie
    finally:
        settings.environment = prev_env
        settings.backend_url = prev_backend
        settings.frontend_url = prev_frontend
