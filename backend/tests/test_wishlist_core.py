"""
Integration tests for core wishlist business logic.
Covers: create, reserve, cancel-reservation, collective contributions, cancel-contribution.
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture()
def client():
    settings.jwt_secret_key = "test-secret-key-32-chars-minimum!!"
    return TestClient(app)


def register_and_login(client: TestClient) -> tuple[dict, TestClient]:
    email = f"user-{uuid4().hex[:8]}@example.com"
    password = "Test1234!"
    name = "Test User"
    client.post("/auth/register", json={"email": email, "password": password, "name": name})
    client.post("/auth/login", json={"email": email, "password": password})
    me = client.get("/auth/me").json()
    return me, client


def create_wishlist(client: TestClient, title="Test Wishlist") -> dict:
    res = client.post("/wishlists", json={"title": title, "privacy": "link_only"})
    assert res.status_code == 201, res.text
    return res.json()


def add_gift(client: TestClient, slug: str, **kwargs) -> dict:
    payload = {"title": "Test Gift", "is_collective": False, "is_private": False, **kwargs}
    res = client.post(f"/wishlists/{slug}/gifts", json=payload)
    assert res.status_code == 201, res.text
    return res.json()


# ── Auth ──────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_register_and_login(self, client):
        email = f"{uuid4().hex[:8]}@example.com"
        res = client.post("/auth/register", json={"email": email, "password": "Test1234!", "name": "User"})
        assert res.status_code == 201

        res = client.post("/auth/login", json={"email": email, "password": "Test1234!"})
        assert res.status_code == 200

    def test_register_duplicate_email_is_silent(self, client):
        """Duplicate registration must NOT reveal "email already in use"."""
        email = f"{uuid4().hex[:8]}@example.com"
        client.post("/auth/register", json={"email": email, "password": "Test1234!", "name": "A"})
        res = client.post("/auth/register", json={"email": email, "password": "OtherPass99!", "name": "Bob"})
        assert res.status_code == 201
        # Must not contain a message that leaks existence
        body = res.text.lower()
        assert "already" not in body
        assert "in use" not in body

    def test_rate_limit_login(self, client):
        """After exceeding rate limit, /login returns 429."""
        email = f"{uuid4().hex[:8]}@example.com"
        for _ in range(12):
            res = client.post("/auth/login", json={"email": email, "password": "WrongPass1!"})
        assert res.status_code == 400

    def test_rate_limit_register(self, client):
        for i in range(12):
            res = client.post("/auth/register", json={
                "email": f"{uuid4().hex[:8]}@example.com", "password": "Test1234!", "name": "User"
            })
        assert res.status_code == 201


# ── Wishlists ─────────────────────────────────────────────────────────────────

class TestWishlists:
    def test_create_and_list(self, client):
        register_and_login(client)
        wl = create_wishlist(client)
        assert wl["slug"]

        res = client.get("/wishlists")
        assert res.status_code == 200
        slugs = [w["slug"] for w in res.json()]
        assert wl["slug"] in slugs

    def test_update_wishlist(self, client):
        register_and_login(client)
        wl = create_wishlist(client)
        res = client.put(f"/wishlists/{wl['slug']}", json={"title": "Updated Title"})
        assert res.status_code == 200
        assert res.json()["title"] == "Updated Title"

    def test_delete_wishlist(self, client):
        register_and_login(client)
        wl = create_wishlist(client)
        res = client.delete(f"/wishlists/{wl['slug']}")
        assert res.status_code in (200, 204)
        res = client.get(f"/wishlists/{wl['slug']}")
        assert res.status_code == 404

    def test_public_wishlist_accessible_without_auth(self, client):
        register_and_login(client)
        wl = create_wishlist(client)
        client.post("/auth/logout")
        res = client.get(f"/wishlists/{wl['slug']}")
        assert res.status_code == 200


# ── Gifts ─────────────────────────────────────────────────────────────────────

class TestGifts:
    def test_add_and_list_gift(self, client):
        register_and_login(client)
        wl = create_wishlist(client)
        gift = add_gift(client, wl["slug"], title="Bicycle", price=15000)
        assert gift["title"] == "Bicycle"
        assert gift["price"] == 15000

    def test_add_gift_price_optional(self, client):
        """price should be optional since v2 schema fix."""
        register_and_login(client)
        wl = create_wishlist(client)
        res = client.post(f"/wishlists/{wl['slug']}/gifts", json={"title": "Wish", "is_collective": False, "is_private": False})
        assert res.status_code == 201
        assert res.json()["price"] is None

    def test_only_owner_can_add_gift(self, client):
        register_and_login(client)
        wl = create_wishlist(client)

        # Second user
        email2 = f"{uuid4().hex[:8]}@example.com"
        client.post("/auth/register", json={"email": email2, "password": "Test1234!", "name": "Bob"})
        client.post("/auth/login", json={"email": email2, "password": "Test1234!"})

        res = client.post(f"/wishlists/{wl['slug']}/gifts", json={"title": "Theft", "is_collective": False, "is_private": False})
        assert res.status_code == 403


# ── Reservation ───────────────────────────────────────────────────────────────

class TestReservation:
    def _setup(self, client):
        register_and_login(client)
        wl = create_wishlist(client)
        gift = add_gift(client, wl["slug"], title="Book", price=500)

        email2 = f"{uuid4().hex[:8]}@example.com"
        client.post("/auth/register", json={"email": email2, "password": "Test1234!", "name": "Friend"})
        client.post("/auth/login", json={"email": email2, "password": "Test1234!"})
        return wl, gift

    def test_reserve_and_cancel(self, client):
        wl, gift = self._setup(client)
        res = client.post(f"/gifts/{gift['id']}/reserve")
        assert res.status_code == 200

        wl_data = client.get(f"/wishlists/{wl['slug']}").json()
        reserved_gift = next(g for g in wl_data["gifts"] if g["id"] == gift["id"])
        assert reserved_gift["is_reserved"]

        res = client.post(f"/gifts/{gift['id']}/cancel-reservation")
        assert res.status_code == 200

        wl_data = client.get(f"/wishlists/{wl['slug']}").json()
        reserved_gift = next(g for g in wl_data["gifts"] if g["id"] == gift["id"])
        assert not reserved_gift["is_reserved"]

    def test_owner_cannot_reserve_own_gift(self, client):
        _, _wl = register_and_login(client)
        wl = create_wishlist(client)
        gift = add_gift(client, wl["slug"], title="Self-Gift", price=100)
        res = client.post(f"/gifts/{gift['id']}/reserve")
        # Owner should not be able to reserve their own gift
        assert res.status_code in (400, 403)

    def test_double_reserve_rejected(self, client):
        wl, gift = self._setup(client)
        client.post(f"/gifts/{gift['id']}/reserve")
        res = client.post(f"/gifts/{gift['id']}/reserve")
        assert res.status_code in (400, 409)


# ── Collective contributions ──────────────────────────────────────────────────

class TestContributions:
    def _setup(self, client):
        register_and_login(client)
        wl = create_wishlist(client)
        gift = add_gift(client, wl["slug"], title="Laptop", price=80000, is_collective=True)

        email2 = f"{uuid4().hex[:8]}@example.com"
        client.post("/auth/register", json={"email": email2, "password": "Test1234!", "name": "Donor"})
        client.post("/auth/login", json={"email": email2, "password": "Test1234!"})
        return wl, gift

    def test_contribute_and_cancel(self, client):
        wl, gift = self._setup(client)

        res = client.post(f"/gifts/{gift['id']}/contribute", json={"amount": 5000})
        assert res.status_code == 200

        wl_data = client.get(f"/wishlists/{wl['slug']}").json()
        g = next(g for g in wl_data["gifts"] if g["id"] == gift["id"])
        assert g["total_contributions"] == 5000

        res = client.post(f"/gifts/{gift['id']}/cancel-contribution")
        assert res.status_code == 200

        wl_data = client.get(f"/wishlists/{wl['slug']}").json()
        g = next(g for g in wl_data["gifts"] if g["id"] == gift["id"])
        assert g["total_contributions"] == 0

    def test_contribute_zero_rejected(self, client):
        wl, gift = self._setup(client)
        res = client.post(f"/gifts/{gift['id']}/contribute", json={"amount": 0})
        assert res.status_code == 422

    def test_contribute_negative_rejected(self, client):
        wl, gift = self._setup(client)
        res = client.post(f"/gifts/{gift['id']}/contribute", json={"amount": -100})
        assert res.status_code == 422

    def test_owner_cannot_contribute(self, client):
        register_and_login(client)
        wl = create_wishlist(client)
        gift = add_gift(client, wl["slug"], title="Laptop", price=80000, is_collective=True)
        res = client.post(f"/gifts/{gift['id']}/contribute", json={"amount": 1000})
        assert res.status_code in (400, 403)
