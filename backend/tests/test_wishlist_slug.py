from urllib.parse import quote

import pytest


@pytest.mark.anyio
async def test_wishlist_slug_decoding(async_client):
    register_payload = {
        "email": "user@example.com",
        "password": "Test1234!",
        "name": "Тестовый Пользователь"
    }
    register_response = await async_client.post("/auth/register", json=register_payload)
    assert register_response.status_code == 201

    login_response = await async_client.post(
        "/auth/login",
        json={"email": register_payload["email"], "password": register_payload["password"]}
    )
    assert login_response.status_code == 200

    wishlist_payload = {
        "title": "др",
        "description": "Описание",
        "event_date": None,
        "privacy": "link_only",
        "is_secret_santa": False
    }
    wishlist_response = await async_client.post("/wishlists", json=wishlist_payload)
    assert wishlist_response.status_code == 201
    slug = wishlist_response.json()["slug"]

    encoded_slug = quote(slug)
    read_response = await async_client.get(f"/wishlists/{encoded_slug}")
    assert read_response.status_code == 200
    assert read_response.json()["slug"] == slug
