import io
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from PIL import Image

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.media import build_media_url, ensure_media_dirs, get_media_root
from app.models.models import User


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])


class UploadImageResponse(BaseModel):
    url: str
    thumb_url: str
    width: int
    height: int
    thumb_width: int
    thumb_height: int


_ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def _validate_upload(file: UploadFile, data: bytes) -> tuple[str, Image.Image]:
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поддерживаются только JPEG, PNG или WebP.",
        )

    max_bytes = int(settings.image_upload_max_mb) * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Размер файла не должен превышать {settings.image_upload_max_mb} МБ.",
        )

    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл не является корректным изображением.",
        )

    fmt = (img.format or "").upper()
    if fmt not in {"JPEG", "PNG", "WEBP"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поддерживаются только JPEG, PNG или WebP.",
        )

    if fmt == "JPEG":
        ext = "jpg"
    elif fmt == "PNG":
        ext = "png"
    else:
        ext = "webp"

    return ext, img


def _save_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(data)


@router.post("/images", response_model=UploadImageResponse)
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> UploadImageResponse:
    _ = current_user
    try:
        ensure_media_dirs()
    except Exception as e:
        logger.error(f"Failed to create media dirs: {e}")
        raise HTTPException(status_code=500, detail="Не удалось создать директорию для загрузки")

    try:
        data = await file.read(int(settings.image_upload_max_mb) * 1024 * 1024 + 1)
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        raise HTTPException(status_code=400, detail="Не удалось прочитать файл")
    
    try:
        ext, img = _validate_upload(file, data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate image: {e}")
        raise HTTPException(status_code=400, detail="Неверный формат изображения")

    media_root = get_media_root() / "gifts"
    image_id = uuid4().hex
    original_name = f"{image_id}.{ext}"
    thumb_name = f"{image_id}_thumb.webp"

    original_path = media_root / original_name
    thumb_path = media_root / thumb_name

    try:
        _save_bytes(original_path, data)
    except Exception as e:
        logger.error(f"Failed to save original: {e}")
        raise HTTPException(status_code=500, detail="Не удалось сохранить изображение")

    try:
        img_for_thumb = img.convert("RGB") if img.mode not in {"RGB", "RGBA"} else img
        if img_for_thumb.mode == "RGBA":
            background = Image.new("RGB", img_for_thumb.size, (255, 255, 255))
            background.paste(img_for_thumb, mask=img_for_thumb.split()[-1])
            img_for_thumb = background

        thumb = img_for_thumb.copy()
        thumb.thumbnail((int(settings.image_thumb_size), int(settings.image_thumb_size)))
        thumb.save(thumb_path, format="WEBP", quality=82, method=6)
    except Exception as e:
        logger.error(f"Failed to create thumbnail: {e}")
        # Continue without thumbnail - original still saved

    url = build_media_url(f"gifts/{original_name}")
    thumb_url = build_media_url(f"gifts/{thumb_name}")

    return UploadImageResponse(
        url=url,
        thumb_url=thumb_url,
        width=int(img.width),
        height=int(img.height),
        thumb_width=int(thumb.width),
        thumb_height=int(thumb.height),
    )

