from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token


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
        assert "samesite=none" in set_cookie.lower()
    finally:
        settings.environment = prev_env
        settings.backend_url = prev_backend
        settings.frontend_url = prev_frontend


def test_auth_me_requires_token():
    client = TestClient(app)
    res = client.get("/auth/me")
    assert res.status_code == 401


def test_auth_me_invalid_token_format():
    client = TestClient(app)
    res = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert res.status_code == 401


def test_auth_me_expired_token():
    client = TestClient(app)
    email = f"user-{uuid4().hex}@example.com"
    password = "Test1234!"
    client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": "User"},
    )
    login_res = client.post("/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200
    user_id = login_res.json().get("id")
    expired = create_access_token(str(user_id), expires_delta_minutes=-1)
    # Create a new client without cookies to test only Bearer token
    fresh_client = TestClient(app)
    res = fresh_client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert res.status_code == 401


def test_refresh_token_flow():
    client = TestClient(app)
    email = f"user-{uuid4().hex}@example.com"
    password = "Test1234!"
    client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": "User"},
    )
    login_res = client.post("/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200
    res = client.post("/auth/refresh")
    assert res.status_code == 204
    refreshed = res.headers.get("set-cookie", "")
    assert "access_token=" in refreshed
    assert "refresh_token=" in refreshed


def test_refresh_token_invalid():
    client = TestClient(app)
    bad_refresh = create_refresh_token("1", expires_delta_minutes=-1)
    res = client.post("/auth/refresh", cookies={"refresh_token": bad_refresh})
    assert res.status_code == 401


def test_wishlists_requires_auth():
    client = TestClient(app)
    res = client.get("/wishlists")
    assert res.status_code == 401


def test_wishlists_after_login():
    client = TestClient(app)
    email = f"user-{uuid4().hex}@example.com"
    password = "Test1234!"
    client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": "User"},
    )
    login_res = client.post("/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200
    res = client.get("/wishlists")
    assert res.status_code == 200
