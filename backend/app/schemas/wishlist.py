from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator

from app.models.models import PrivacyLevelEnum


class WishlistBase(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    event_date: datetime | None = None
    privacy: PrivacyLevelEnum = PrivacyLevelEnum.LINK_ONLY
    is_secret_santa: bool = False
    access_emails: list[EmailStr] | None = None

    @field_validator("title")
    @classmethod
    def _wishlist_title_strip(cls, value: str) -> str:
        return value.strip()

    @field_validator("description")
    @classmethod
    def _wishlist_description_strip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class WishlistCreate(WishlistBase):
    pass


class WishlistUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    event_date: datetime | None = None
    privacy: PrivacyLevelEnum | None = None
    is_secret_santa: bool | None = None
    access_emails: list[EmailStr] | None = None


class GiftBase(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    url: str | None = None
    price: float | None = Field(default=None, gt=0)
    image_url: str | None = None
    is_collective: bool = False
    is_private: bool = False

    @field_validator("title")
    @classmethod
    def _title_strip(cls, value: str) -> str:
        return value.strip()

    @field_validator("url", "image_url")
    @classmethod
    def _normalize_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class GiftCreate(GiftBase):
    wishlist_id: int


class GiftUpdate(BaseModel):
    title: str | None = None
    url: HttpUrl | None = None
    price: float | None = Field(default=None, gt=0)
    image_url: HttpUrl | None = None
    is_collective: bool | None = None
    is_private: bool | None = None


class ContributionCreate(BaseModel):
    amount: float = Field(gt=0)


class ReservationCreate(BaseModel):
    gift_id: int


class ContributionPublic(BaseModel):
    id: int
    amount: float
    created_at: datetime
    user_id: int
    user_name: str | None = None
    user_email: str | None = None

    class Config:
        from_attributes = True


class ReservationPublic(BaseModel):
    id: int
    created_at: datetime
    user_id: int | None = None
    user_name: str | None = None
    user_email: str | None = None

    class Config:
        from_attributes = True


class GiftPublic(BaseModel):
    id: int
    title: str
    url: str | None
    price: float | None
    image_url: str | None
    is_collective: bool
    is_private: bool
    created_at: datetime
    is_reserved: bool = False
    reservation: ReservationPublic | None
    contributions: list[ContributionPublic]
    total_contributions: float
    collected_percent: float
    is_fully_collected: bool
    is_unavailable: bool = False
    unavailable_reason: str | None = None

    class Config:
        from_attributes = True


class WishlistPublic(BaseModel):
    id: int
    slug: str
    title: str
    description: str | None
    event_date: datetime | None
    privacy: PrivacyLevelEnum
    is_secret_santa: bool
    created_at: datetime
    owner_id: int
    gifts: list[GiftPublic]
    access_emails: list[str] = []
    public_token: str | None = None

    class Config:
        from_attributes = True
