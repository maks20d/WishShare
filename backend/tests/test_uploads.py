import io
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


def _register_and_login(client: TestClient) -> None:
    email = f"user-{uuid4().hex}@example.com"
    password = "SecurePass123!"
    client.post("/auth/register", json={"email": email, "password": password, "name": "User"})
    client.post("/auth/login", json={"email": email, "password": password})


def test_upload_image_ok(tmp_path):
    client = TestClient(app)
    _register_and_login(client)

    buf = io.BytesIO()
    Image.new("RGBA", (1, 1), (255, 0, 0, 255)).save(buf, format="PNG")
    png_bytes = buf.getvalue()

    res = client.post(
        "/uploads/images",
        files={"file": ("test.png", png_bytes, "image/png")},
    )
    assert res.status_code == 200
    data = res.json()
    assert "url" in data and "thumb_url" in data
    assert data["url"].endswith(".png")
    assert data["thumb_url"].endswith("_thumb.webp")
    assert data["width"] == 1
    assert data["height"] == 1

    url_path = urlparse(data["url"]).path
    thumb_path = urlparse(data["thumb_url"]).path
    assert client.get(url_path).status_code == 200
    assert client.get(thumb_path).status_code == 200

    uploads_dir = Path(__file__).resolve().parents[1] / "uploads-test" / "gifts"
    assert uploads_dir.exists()


def test_upload_image_rejects_wrong_type():
    client = TestClient(app)
    _register_and_login(client)

    res = client.post(
        "/uploads/images",
        files={"file": ("test.txt", b"nope", "text/plain")},
    )
    assert res.status_code == 400


def test_upload_image_rejects_too_large():
    client = TestClient(app)
    _register_and_login(client)

    payload = b"0" * (5 * 1024 * 1024 + 1)
    res = client.post(
        "/uploads/images",
        files={"file": ("big.png", payload, "image/png")},
    )
    assert res.status_code == 413
