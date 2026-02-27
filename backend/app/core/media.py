from pathlib import Path

from app.core.config import settings


_BACKEND_DIR = Path(__file__).resolve().parents[2]


def get_media_root() -> Path:
    root = Path(settings.media_root)
    if root.is_absolute():
        return root
    return _BACKEND_DIR / root


def ensure_media_dirs() -> None:
    root = get_media_root()
    root.mkdir(parents=True, exist_ok=True)
    (root / "gifts").mkdir(parents=True, exist_ok=True)


def build_media_url(relative_path: str) -> str:
    base = settings.backend_url.rstrip("/")
    rel = relative_path.lstrip("/")
    return f"{base}{settings.media_path.rstrip('/')}/{rel}"

