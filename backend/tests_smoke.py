import random
import string
import sys

import httpx


BASE_URL = "http://localhost:8000"


def _random_email() -> str:
    suffix = "".join(random.choice(string.ascii_lowercase) for _ in range(6))
    return f"test{suffix}@example.com"


def _register_and_login(session: httpx.Client, email: str, password: str, name: str) -> None:
    register_payload = {"email": email, "password": password, "name": name}
    r = session.post(f"{BASE_URL}/auth/register", json=register_payload)
    print("status", r.status_code)
    print(r.text)
    if r.status_code not in (200, 201, 400):
        print("Unexpected register status")
        sys.exit(1)

    r = session.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    print("status", r.status_code)
    print(r.text)
    if not r.is_success:
        print("Login failed")
        sys.exit(1)


def main() -> None:
    owner_session = httpx.Client(timeout=20.0)

    # Регистрация
    email = _random_email()
    password = "Test1234!"
    print("=== REGISTER ===")
    _register_and_login(owner_session, email, password, "Тестовый Пользователь")

    print("=== FORGOT PASSWORD ===")
    r = owner_session.post(f"{BASE_URL}/auth/forgot-password", json={"email": email})
    print("status", r.status_code)
    if r.status_code != 204:
        print("Forgot password failed")
        sys.exit(1)

    print("=== REGISTER FRIEND ===")
    friend_session = httpx.Client(timeout=20.0)
    friend_email = _random_email()
    _register_and_login(friend_session, friend_email, password, "Тестовый Друг")

    # Создание вишлиста
    print("=== CREATE WISHLIST ===")
    wl_payload = {
        "title": "Автотест вишлист",
        "description": "",
        "event_date": None,
        "privacy": "link_only",
        "is_secret_santa": False,
    }
    r = owner_session.post(f"{BASE_URL}/wishlists", json=wl_payload)
    print("status", r.status_code)
    print(r.text)
    if not r.is_success:
        print("Wishlist creation failed")
        sys.exit(1)

    slug = r.json().get("slug")
    print("slug", slug)
    if not slug:
        print("No slug in wishlist response")
        sys.exit(1)

    # OG preview – корректный URL
    print("=== OG PREVIEW VALID ===")
    r = owner_session.post(f"{BASE_URL}/parse-url", json={"url": "https://example.com"})
    print("status", r.status_code)
    print(r.text[:200])
    if not r.is_success:
        print("OG preview (valid) failed")
        sys.exit(1)
    parsed = r.json()
    for key in ("url", "title", "price", "image_url", "description", "brand", "currency", "availability"):
        if key not in parsed:
            print(f"OG preview (valid) missing key: {key}")
            sys.exit(1)

    # OG preview – «грязный» URL
    print("=== OG PREVIEW DIRTY ===")
    r = owner_session.post(f"{BASE_URL}/parse-url", json={"url": "  https: example.com"})
    print("status", r.status_code)
    print(r.text[:200])
    if not r.is_success:
        print("OG preview (dirty) failed")
        sys.exit(1)
    parsed = r.json()
    for key in ("url", "title", "price", "image_url", "description", "brand", "currency", "availability"):
        if key not in parsed:
            print(f"OG preview (dirty) missing key: {key}")
            sys.exit(1)

    # Создание обычного подарка и проверка бронирования
    print("=== CREATE NON-COLLECTIVE GIFT ===")
    single_gift_payload = {
        "title": "Обычный подарок",
        "url": "https://example.com/gift",
        "price": 5_000,
        "image_url": None,
        "is_collective": False,
        "is_private": False,
    }
    r = owner_session.post(f"{BASE_URL}/wishlists/{slug}/gifts", json=single_gift_payload)
    print("status", r.status_code)
    print(r.text)
    if not r.is_success:
        print("Non-collective gift creation failed")
        sys.exit(1)

    gift_id = r.json().get("id")
    if not gift_id:
        print("No gift id in response")
        sys.exit(1)

    print("=== RESERVE GIFT ===")
    r = friend_session.post(f"{BASE_URL}/gifts/{gift_id}/reserve")
    print("status", r.status_code)
    print(r.text)
    if not r.is_success:
        print("Gift reservation failed")
        sys.exit(1)

    print("=== CHECK RESERVER VISIBILITY FOR FRIEND ===")
    r = friend_session.get(f"{BASE_URL}/wishlists/{slug}")
    print("status", r.status_code)
    print(r.text)
    if not r.is_success:
        print("Wishlist read failed")
        sys.exit(1)
    reservation = r.json()["gifts"][0].get("reservation") or {}
    if not reservation.get("user_name") and not reservation.get("user_email"):
        print("Friend view does not include reserver identity")
        sys.exit(1)

    print("=== CANCEL RESERVATION ===")
    r = friend_session.post(f"{BASE_URL}/gifts/{gift_id}/cancel-reservation")
    print("status", r.status_code)
    print(r.text)
    if not r.is_success:
        print("Cancel reservation failed")
        sys.exit(1)

    print("=== UPDATE GIFT ===")
    update_payload = {
        "title": "Обычный подарок (обновлён)",
        "price": 5500,
        "is_collective": False,
        "is_private": True,
    }
    r = owner_session.put(f"{BASE_URL}/gifts/{gift_id}", json=update_payload)
    print("status", r.status_code)
    print(r.text)
    if not r.is_success:
        print("Gift update failed")
        sys.exit(1)

    updated = r.json()
    if updated.get("is_private") is not True:
        print("Gift update returned invalid is_private value")
        sys.exit(1)
    try:
        updated_price = float(updated.get("price"))
    except (TypeError, ValueError):
        print("Gift update returned invalid price value")
        sys.exit(1)
    if abs(updated_price - 5500.0) > 0.001:
        print("Gift update returned unexpected price")
        sys.exit(1)

    # Создание коллективного подарка
    print("=== CREATE COLLECTIVE GIFT ===")
    gift_payload = {
        "title": "Тестовый коллективный подарок",
        "url": "wildberries.ru/test",
        "price": 10_000,
        "image_url": None,
        "is_collective": True,
        "is_private": False,
    }
    r = owner_session.post(f"{BASE_URL}/wishlists/{slug}/gifts", json=gift_payload)
    print("status", r.status_code)
    print(r.text)
    if not r.is_success:
        print("Collective gift creation failed")
        sys.exit(1)

    print("=== SMOKE TEST PASSED ===")


if __name__ == "__main__":
    main()
