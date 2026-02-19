from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSessionDep, get_current_user, get_optional_user
from app.models.models import Contribution, Gift, PrivacyLevelEnum, Reservation, User, Wishlist, WishlistAccessEmail
from app.realtime.manager import manager
from uuid import uuid4
from app.schemas.wishlist import (
    ContributionCreate,
    GiftBase,
    GiftPublic,
    GiftUpdate,
    WishlistCreate,
    WishlistPublic,
    WishlistUpdate,
)


router = APIRouter(prefix="/wishlists", tags=["wishlists"])
compat_router = APIRouter(tags=["wishlists"])


def _compute_gift_progress(price: float | None, total_contributions: float) -> tuple[float, bool]:
    if not price or price <= 0:
        return 0.0, False
    percent = min(float(total_contributions) / float(price) * 100.0, 100.0)
    return percent, percent >= 100.0


def _serialize_gift(
    gift: Gift,
    total_contributions: float,
    viewer_role: str,
    user_lookup: dict[int, User] | None = None,
    is_secret_santa: bool = False,
) -> GiftPublic:
    user_lookup = user_lookup or {}
    role_for_sensitive = viewer_role
    if is_secret_santa and viewer_role != "owner":
        role_for_sensitive = "public"
    collected_percent, is_fully_collected = _compute_gift_progress(
        float(gift.price) if gift.price is not None else None,
        total_contributions,
    )
    is_reserved = gift.reservation is not None

    if viewer_role == "owner":
        return GiftPublic(
            id=gift.id,
            title=gift.title,
            url=gift.url,
            price=float(gift.price) if gift.price is not None else None,
            image_url=gift.image_url,
            is_collective=gift.is_collective,
            is_private=gift.is_private,
            created_at=gift.created_at,
            is_reserved=is_reserved,
            reservation=None,
            contributions=[],
            total_contributions=float(total_contributions),
            collected_percent=collected_percent,
            is_fully_collected=is_fully_collected,
            is_unavailable=getattr(gift, "is_unavailable", False),
            unavailable_reason=getattr(gift, "unavailable_reason", None),
        )

    reservation_public = None
    if gift.reservation:
        from app.schemas.wishlist import ReservationPublic

        reservation_user = user_lookup.get(gift.reservation.user_id)
        if role_for_sensitive == "friend":
            reservation_public = ReservationPublic(
                id=gift.reservation.id,
                created_at=gift.reservation.created_at,
                user_id=gift.reservation.user_id,
                user_name=reservation_user.name if reservation_user else None,
                user_email=reservation_user.email if reservation_user else None,
            )
        else:
            reservation_public = ReservationPublic(
                id=gift.reservation.id,
                created_at=gift.reservation.created_at,
                user_id=None,
            )

    from app.schemas.wishlist import ContributionPublic

    contributions_public: list[ContributionPublic] = []
    if role_for_sensitive == "friend":
        contributions_public = [
            ContributionPublic(
                id=c.id,
                amount=float(c.amount),
                created_at=c.created_at,
                user_id=c.user_id,
                user_name=user_lookup.get(c.user_id).name if c.user_id in user_lookup else None,
                user_email=user_lookup.get(c.user_id).email if c.user_id in user_lookup else None,
            )
            for c in gift.contributions
        ]

    return GiftPublic(
        id=gift.id,
        title=gift.title,
        url=gift.url,
        price=float(gift.price) if gift.price is not None else None,
        image_url=gift.image_url,
        is_collective=gift.is_collective,
        is_private=gift.is_private,
        created_at=gift.created_at,
        is_reserved=is_reserved,
        reservation=reservation_public,
        contributions=contributions_public if viewer_role == "friend" else [],
        total_contributions=float(total_contributions),
        collected_percent=collected_percent,
        is_fully_collected=is_fully_collected,
        is_unavailable=getattr(gift, "is_unavailable", False),
        unavailable_reason=getattr(gift, "unavailable_reason", None),
    )


def _ws_gift_payload(gift: Gift, payload: GiftPublic, viewer_role: str) -> dict[str, Any]:
    if gift.is_private and viewer_role != "owner":
        return {"id": gift.id, "hidden": True}
    return payload.model_dump()


def _normalize_access_emails(emails: list[str] | None) -> list[str]:
    if not emails:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for email in emails:
        value = (email or "").strip().lower()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


async def _load_wishlist_with_gifts(
    db: AsyncSession,
    wishlist: Wishlist,
    viewer: User | None,
) -> WishlistPublic:
    import logging
    logger = logging.getLogger("wishshare.wishlists")
    
    logger.debug("_load_wishlist_with_gifts: start wishlist_id=%s slug=%s", wishlist.id, wishlist.slug)
    
    viewer_role = "public"
    if viewer and viewer.id == wishlist.owner_id:
        viewer_role = "owner"
    elif viewer:
        viewer_role = "friend"
    
    logger.debug("_load_wishlist_with_gifts: viewer_role=%s", viewer_role)

    try:
        gifts_result = await db.execute(
            select(Gift)
            .where(Gift.wishlist_id == wishlist.id)
            .order_by(Gift.created_at.asc())
        )
        gifts = list(gifts_result.scalars().unique())
        logger.debug("_load_wishlist_with_gifts: found %d gifts", len(gifts))
    except Exception as e:
        logger.exception("_load_wishlist_with_gifts: failed to load gifts for wishlist_id=%s", wishlist.id)
        raise

    contributions_map: dict[int, float] = {}
    if gifts:
        try:
            contributions_result = await db.execute(
                select(
                    Contribution.gift_id,
                    func.coalesce(func.sum(Contribution.amount), 0),
                ).where(Contribution.gift_id.in_([g.id for g in gifts]))
                .group_by(Contribution.gift_id)
            )
            contributions_map = {
                row[0]: float(row[1]) for row in contributions_result.all()
            }
            logger.debug("_load_wishlist_with_gifts: loaded contributions for %d gifts", len(contributions_map))
        except Exception as e:
            logger.exception("_load_wishlist_with_gifts: failed to load contributions")
            raise

    try:
        for gift in gifts:
            await db.refresh(gift, attribute_names=["reservation", "contributions"])
        logger.debug("_load_wishlist_with_gifts: refreshed gifts relationships")
    except Exception as e:
        logger.exception("_load_wishlist_with_gifts: failed to refresh gifts")
        raise

    user_ids: set[int] = set()
    for gift in gifts:
        if gift.reservation:
            user_ids.add(gift.reservation.user_id)
        for contribution in gift.contributions:
            user_ids.add(contribution.user_id)
    
    logger.debug("_load_wishlist_with_gifts: found %d user_ids to load", len(user_ids))

    user_lookup: dict[int, User] = {}
    if user_ids:
        try:
            users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
            users = list(users_result.scalars().unique())
            user_lookup = {u.id: u for u in users}
            logger.debug("_load_wishlist_with_gifts: loaded %d users", len(user_lookup))
        except Exception as e:
            logger.exception("_load_wishlist_with_gifts: failed to load users")
            raise

    try:
        gift_public_list = [
            _serialize_gift(
                gift,
                contributions_map.get(gift.id, 0.0),
                viewer_role=viewer_role,
                user_lookup=user_lookup,
                is_secret_santa=wishlist.is_secret_santa,
            )
            for gift in gifts
            if not (gift.is_private and viewer_role != "owner")
        ]
        logger.debug("_load_wishlist_with_gifts: serialized %d gifts", len(gift_public_list))
    except Exception as e:
        logger.exception("_load_wishlist_with_gifts: failed to serialize gifts")
        raise

    access_emails: list[str] = []
    if viewer_role == "owner":
        try:
            access_result = await db.execute(
                select(WishlistAccessEmail.email)
                .where(WishlistAccessEmail.wishlist_id == wishlist.id)
                .order_by(WishlistAccessEmail.email.asc())
            )
            access_emails = [row[0] for row in access_result.all()]
            logger.debug("_load_wishlist_with_gifts: loaded %d access_emails", len(access_emails))
        except Exception as e:
            logger.exception("_load_wishlist_with_gifts: failed to load access_emails")
            raise

    try:
        # Convert privacy string to enum if needed
        privacy_value = wishlist.privacy
        if isinstance(privacy_value, str):
            privacy_value = PrivacyLevelEnum(privacy_value)
        
        result = WishlistPublic(
            id=wishlist.id,
            slug=wishlist.slug,
            title=wishlist.title,
            description=wishlist.description,
            event_date=wishlist.event_date,
            privacy=privacy_value,
            is_secret_santa=wishlist.is_secret_santa,
            created_at=wishlist.created_at,
            owner_id=wishlist.owner_id,
            gifts=gift_public_list,
            access_emails=access_emails,
            public_token=wishlist.public_token if viewer_role == "owner" else None,
        )
        logger.debug("_load_wishlist_with_gifts: successfully created WishlistPublic for wishlist_id=%s", wishlist.id)
        return result
    except Exception as e:
        logger.exception("_load_wishlist_with_gifts: failed to create WishlistPublic for wishlist_id=%s", wishlist.id)
        raise


async def _has_friends_access(db: AsyncSession, wishlist: Wishlist, viewer: User | None) -> bool:
    if not viewer:
        return False
    if viewer.id == wishlist.owner_id:
        return True
    normalized = (viewer.email or "").strip().lower()
    if not normalized:
        return False
    access_result = await db.execute(
        select(WishlistAccessEmail.email).where(WishlistAccessEmail.wishlist_id == wishlist.id)
    )
    allowed = {row[0].strip().lower() for row in access_result.all() if row[0]}
    return normalized in allowed


def _slugify(title: str) -> str:
    import re

    slug = title.strip().lower()
    slug = re.sub(r"[^a-z0-9а-яё]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "wishlist"


@router.get("", response_model=list[WishlistPublic])
@router.get("/my", response_model=list[WishlistPublic])
async def list_my_wishlists(
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> list[WishlistPublic]:
    import logging
    logger = logging.getLogger("wishshare.wishlists")
    
    logger.info("list_my_wishlists: starting for user_id=%s", current_user.id)
    
    try:
        result = await db.execute(
            select(Wishlist).where(Wishlist.owner_id == current_user.id).order_by(Wishlist.created_at.desc())
        )
        wishlists = list(result.scalars().unique())
        logger.info("list_my_wishlists: found %d wishlists for user_id=%s", len(wishlists), current_user.id)
    except Exception as e:
        logger.exception("list_my_wishlists: DB query failed for user_id=%s", current_user.id)
        raise HTTPException(status_code=500, detail="Database query failed")
    
    result_list = []
    for idx, w in enumerate(wishlists):
        try:
            logger.debug("list_my_wishlists: processing wishlist %d (id=%s, slug=%s)", idx, w.id, w.slug)
            loaded = await _load_wishlist_with_gifts(db, w, current_user)
            result_list.append(loaded)
        except Exception as e:
            logger.exception("list_my_wishlists: failed to load wishlist id=%s slug=%s: %s", w.id, w.slug, str(e))
            raise HTTPException(status_code=500, detail=f"Failed to load wishlist {w.slug}: {str(e)}")
    
    logger.info("list_my_wishlists: successfully returned %d wishlists for user_id=%s", len(result_list), current_user.id)
    return result_list


@router.put("/{slug}", response_model=WishlistPublic)
async def update_wishlist(
    slug: str,
    payload: WishlistUpdate,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> WishlistPublic:
    result = await db.execute(select(Wishlist).where(Wishlist.slug == slug))
    wishlist = result.scalar_one_or_none()
    if not wishlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist not found")

    if wishlist.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can update wishlist")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(wishlist, key):
            if key == "privacy" and hasattr(value, "value"):
                setattr(wishlist, key, value.value)
            else:
                setattr(wishlist, key, value)

    if "access_emails" in update_data:
        normalized_emails = _normalize_access_emails(payload.access_emails)
        wishlist.access_emails = [
            WishlistAccessEmail(email=email) for email in normalized_emails
        ]

    await db.commit()
    await db.refresh(wishlist)
    return await _load_wishlist_with_gifts(db, wishlist, current_user)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wishlist(
    slug: str,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(select(Wishlist).where(Wishlist.slug == slug))
    wishlist = result.scalar_one_or_none()
    if not wishlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist not found")

    if wishlist.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can delete wishlist")

    await db.delete(wishlist)
    await db.commit()


@router.post("", response_model=WishlistPublic, status_code=status.HTTP_201_CREATED)
async def create_wishlist(
    payload: WishlistCreate,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> WishlistPublic:
    base_slug = _slugify(payload.title)
    slug = base_slug
    suffix = 1
    while True:
        existing = await db.execute(select(Wishlist).where(Wishlist.slug == slug))
        if not existing.scalar_one_or_none():
            break
        suffix += 1
        slug = f"{base_slug}-{suffix}"

    wishlist = Wishlist(
        owner_id=current_user.id,
        title=payload.title,
        description=payload.description,
        event_date=payload.event_date,
        privacy=payload.privacy.value if hasattr(payload.privacy, "value") else payload.privacy,
        is_secret_santa=payload.is_secret_santa,
        slug=slug,
        created_at=datetime.utcnow(),
        public_token=str(uuid4()),
    )
    normalized_emails = _normalize_access_emails(payload.access_emails)
    if normalized_emails:
        wishlist.access_emails = [
            WishlistAccessEmail(email=email) for email in normalized_emails
        ]
    db.add(wishlist)
    await db.commit()
    await db.refresh(wishlist)
    return await _load_wishlist_with_gifts(db, wishlist, current_user)


@router.get("/token/{token}", response_model=WishlistPublic)
async def get_wishlist_by_token(
    token: str,
    db: DbSessionDep,
    response: Response,
) -> WishlistPublic:
    result = await db.execute(select(Wishlist).where(Wishlist.public_token == token))
    wishlist = result.scalar_one_or_none()
    if not wishlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist not found")

    if wishlist.privacy not in ("public", "link_only"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    response.headers["Cache-Control"] = "public, max-age=60"
    return await _load_wishlist_with_gifts(db, wishlist, None)


@router.post("/{slug}/rotate-token")
async def rotate_public_token(
    slug: str,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    result = await db.execute(select(Wishlist).where(Wishlist.slug == slug))
    wishlist = result.scalar_one_or_none()
    if not wishlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist not found")
    if wishlist.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can rotate token")
    wishlist.public_token = str(uuid4())
    await db.commit()
    await db.refresh(wishlist)
    return {"public_token": wishlist.public_token}


@router.get("/{slug}", response_model=WishlistPublic)
async def get_wishlist_by_slug(
    slug: str,
    db: DbSessionDep,
    viewer: User | None = Depends(get_optional_user),
) -> WishlistPublic:
    result = await db.execute(select(Wishlist).where(Wishlist.slug == slug))
    wishlist = result.scalar_one_or_none()
    if not wishlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist not found")

    if wishlist.privacy in ("public", "link_only"):
        return await _load_wishlist_with_gifts(db, wishlist, viewer)

    if not viewer:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    if wishlist.privacy == "friends":
        has_access = await _has_friends_access(db, wishlist, viewer)
        if not has_access:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return await _load_wishlist_with_gifts(db, wishlist, viewer)

    return await _load_wishlist_with_gifts(db, wishlist, viewer)


@router.post("/{slug}/gifts", response_model=GiftPublic, status_code=status.HTTP_201_CREATED)
async def add_gift_to_wishlist(
    slug: str,
    payload: GiftBase,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> GiftPublic:
    result = await db.execute(select(Wishlist).where(Wishlist.slug == slug))
    wishlist = result.scalar_one_or_none()
    if not wishlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist not found")

    if wishlist.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can add gifts")

    gift = Gift(
        wishlist_id=wishlist.id,
        title=payload.title,
        url=str(payload.url) if payload.url else None,
        price=payload.price,
        image_url=str(payload.image_url) if payload.image_url else None,
        is_collective=payload.is_collective,
        is_private=payload.is_private,
    )
    db.add(gift)
    await db.commit()
    await db.refresh(gift, attribute_names=["reservation", "contributions"])

    owner_view = _serialize_gift(
        gift,
        total_contributions=0.0,
        viewer_role="owner",
        is_secret_santa=wishlist.is_secret_santa,
    )
    friend_view = _serialize_gift(
        gift,
        total_contributions=0.0,
        viewer_role="friend",
        is_secret_santa=wishlist.is_secret_santa,
    )
    public_view = _serialize_gift(
        gift,
        total_contributions=0.0,
        viewer_role="public",
        is_secret_santa=wishlist.is_secret_santa,
    )

    await manager.broadcast_gift_event(
        wishlist.slug,
        event_type="gift_created",
        payload_for_owner=_ws_gift_payload(gift, owner_view, "owner"),
        payload_for_friend=_ws_gift_payload(gift, friend_view, "friend"),
        payload_for_public=_ws_gift_payload(gift, public_view, "public"),
    )

    return owner_view


@router.post("/gifts/{gift_id}/reserve", response_model=GiftPublic)
async def reserve_gift(
    gift_id: int,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> GiftPublic:
    # Reservation rules: non-collective, non-owner, public/non-private, single active reservation.
    gift_result = await db.execute(select(Gift).where(Gift.id == gift_id))
    gift = gift_result.scalar_one_or_none()
    if not gift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found")

    await db.refresh(gift, attribute_names=["reservation", "contributions", "wishlist"])

    if gift.is_collective:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot reserve collective gift")

    if gift.is_private and gift.wishlist.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Gift is private")

    if gift.wishlist.owner_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner cannot reserve own gift")

    if gift.reservation:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gift already reserved")

    reservation = Reservation(gift_id=gift.id, user_id=current_user.id)
    db.add(reservation)
    await db.commit()
    await db.refresh(gift, attribute_names=["reservation", "contributions", "wishlist"])

    contributions_total_result = await db.execute(
        select(func.coalesce(func.sum(Contribution.amount), 0)).where(Contribution.gift_id == gift.id)
    )
    total_contributions = float(contributions_total_result.scalar_one())

    viewer_role = "owner" if gift.wishlist.owner_id == current_user.id else "friend"

    owner_view = _serialize_gift(
        gift,
        total_contributions=total_contributions,
        viewer_role="owner",
        is_secret_santa=gift.wishlist.is_secret_santa,
    )
    friend_view = _serialize_gift(
        gift,
        total_contributions=total_contributions,
        viewer_role="friend",
        is_secret_santa=gift.wishlist.is_secret_santa,
    )
    public_view = _serialize_gift(
        gift,
        total_contributions=total_contributions,
        viewer_role="public",
        is_secret_santa=gift.wishlist.is_secret_santa,
    )

    await manager.broadcast_gift_event(
        gift.wishlist.slug,
        event_type="gift_reserved",
        payload_for_owner=_ws_gift_payload(gift, owner_view, "owner"),
        payload_for_friend=_ws_gift_payload(gift, friend_view, "friend"),
        payload_for_public=_ws_gift_payload(gift, public_view, "public"),
    )

    return _serialize_gift(
        gift,
        total_contributions=total_contributions,
        viewer_role=viewer_role,
        is_secret_santa=gift.wishlist.is_secret_santa,
    )


@router.post("/gifts/{gift_id}/cancel-reservation", response_model=GiftPublic)
async def cancel_reservation(
    gift_id: int,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> GiftPublic:
    gift_result = await db.execute(select(Gift).where(Gift.id == gift_id))
    gift = gift_result.scalar_one_or_none()
    if not gift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found")

    await db.refresh(gift, attribute_names=["reservation", "contributions", "wishlist"])
    if not gift.reservation:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gift not reserved")

    if gift.reservation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only reserver can cancel")

    await db.delete(gift.reservation)
    await db.commit()
    await db.refresh(gift, attribute_names=["reservation", "contributions", "wishlist"])

    contributions_total_result = await db.execute(
        select(func.coalesce(func.sum(Contribution.amount), 0)).where(Contribution.gift_id == gift.id)
    )
    total_contributions = float(contributions_total_result.scalar_one())

    viewer_role = "owner" if gift.wishlist.owner_id == current_user.id else "friend"

    owner_view = _serialize_gift(
        gift,
        total_contributions=total_contributions,
        viewer_role="owner",
        is_secret_santa=gift.wishlist.is_secret_santa,
    )
    friend_view = _serialize_gift(
        gift,
        total_contributions=total_contributions,
        viewer_role="friend",
        is_secret_santa=gift.wishlist.is_secret_santa,
    )
    public_view = _serialize_gift(
        gift,
        total_contributions=total_contributions,
        viewer_role="public",
        is_secret_santa=gift.wishlist.is_secret_santa,
    )

    await manager.broadcast_gift_event(
        gift.wishlist.slug,
        event_type="reservation_canceled",
        payload_for_owner=_ws_gift_payload(gift, owner_view, "owner"),
        payload_for_friend=_ws_gift_payload(gift, friend_view, "friend"),
        payload_for_public=_ws_gift_payload(gift, public_view, "public"),
    )

    return _serialize_gift(
        gift,
        total_contributions=total_contributions,
        viewer_role=viewer_role,
        is_secret_santa=gift.wishlist.is_secret_santa,
    )


@router.post("/gifts/{gift_id}/contribute", response_model=GiftPublic)
async def contribute_to_gift(
    payload: ContributionCreate,
    gift_id: int,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> GiftPublic:
    if payload.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be positive")

    gift_result = await db.execute(select(Gift).where(Gift.id == gift_id))
    gift = gift_result.scalar_one_or_none()
    if not gift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found")

    await db.refresh(gift, attribute_names=["reservation", "contributions", "wishlist"])

    if not gift.is_collective:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gift is not collective")

    if gift.is_private and gift.wishlist.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Gift is private")

    if gift.wishlist.owner_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner cannot contribute")

    if gift.price is None or gift.price <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gift price is required")

    contributions_total_result = await db.execute(
        select(func.coalesce(func.sum(Contribution.amount), 0)).where(Contribution.gift_id == gift.id)
    )
    total_contributions = float(contributions_total_result.scalar_one())

    remaining = float(gift.price) - total_contributions
    if remaining <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gift already fully collected")

    min_share = max(float(gift.price) * 0.1, 1.0)
    effective_min = min(min_share, remaining)

    if payload.amount < effective_min:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum contribution is {effective_min}",
        )

    if payload.amount > remaining:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum contribution is {remaining}",
        )

    contribution = Contribution(
        gift_id=gift.id,
        user_id=current_user.id,
        amount=payload.amount,
    )
    db.add(contribution)
    # append-only donation ledger (best-effort)
    try:
        from app.models.models import WishlistDonation
        donation = WishlistDonation(
            wishlist_id=gift.wishlist_id,
            gift_id=gift.id,
            user_id=current_user.id,
            amount=payload.amount,
        )
        db.add(donation)
    except Exception:
        pass
    await db.commit()
    await db.refresh(gift, attribute_names=["reservation", "contributions", "wishlist"])

    contributions_total_result = await db.execute(
        select(func.coalesce(func.sum(Contribution.amount), 0)).where(Contribution.gift_id == gift.id)
    )
    total_contributions = float(contributions_total_result.scalar_one())

    viewer_role = "owner" if gift.wishlist.owner_id == current_user.id else "friend"

    owner_view = _serialize_gift(
        gift,
        total_contributions=total_contributions,
        viewer_role="owner",
        is_secret_santa=gift.wishlist.is_secret_santa,
    )
    friend_view = _serialize_gift(
        gift,
        total_contributions=total_contributions,
        viewer_role="friend",
        is_secret_santa=gift.wishlist.is_secret_santa,
    )
    public_view = _serialize_gift(
        gift,
        total_contributions=total_contributions,
        viewer_role="public",
        is_secret_santa=gift.wishlist.is_secret_santa,
    )

    await manager.broadcast_gift_event(
        gift.wishlist.slug,
        event_type="contribution_added",
        payload_for_owner=_ws_gift_payload(gift, owner_view, "owner"),
        payload_for_friend=_ws_gift_payload(gift, friend_view, "friend"),
        payload_for_public=_ws_gift_payload(gift, public_view, "public"),
    )

    return _serialize_gift(
        gift,
        total_contributions=total_contributions,
        viewer_role=viewer_role,
        is_secret_santa=gift.wishlist.is_secret_santa,
    )


@router.put("/gifts/{gift_id}", response_model=GiftPublic)
async def update_gift(
    gift_id: int,
    payload: GiftUpdate,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> GiftPublic:
    gift_result = await db.execute(select(Gift).where(Gift.id == gift_id))
    gift = gift_result.scalar_one_or_none()
    if not gift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found")

    await db.refresh(gift, attribute_names=["reservation", "contributions", "wishlist"])

    if gift.wishlist.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can update gift")

    # Price must stay stable once there are active reservations/contributions.
    if payload.price is not None and payload.price != gift.price:
        if gift.reservation or gift.contributions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change price of gift with active reservations or contributions",
            )

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if not hasattr(gift, key) or value is None:
            continue
        if key in {"url", "image_url"}:
            setattr(gift, key, str(value))
        else:
            setattr(gift, key, value)

    await db.commit()
    await db.refresh(gift, attribute_names=["reservation", "contributions", "wishlist"])

    contributions_total_result = await db.execute(
        select(func.coalesce(func.sum(Contribution.amount), 0)).where(Contribution.gift_id == gift.id)
    )
    total_contributions = float(contributions_total_result.scalar_one())

    owner_view = _serialize_gift(
        gift,
        total_contributions=total_contributions,
        viewer_role="owner",
        is_secret_santa=gift.wishlist.is_secret_santa,
    )
    friend_view = _serialize_gift(
        gift,
        total_contributions=total_contributions,
        viewer_role="friend",
        is_secret_santa=gift.wishlist.is_secret_santa,
    )
    public_view = _serialize_gift(
        gift,
        total_contributions=total_contributions,
        viewer_role="public",
        is_secret_santa=gift.wishlist.is_secret_santa,
    )

    await manager.broadcast_gift_event(
        gift.wishlist.slug,
        event_type="gift_updated",
        payload_for_owner=_ws_gift_payload(gift, owner_view, "owner"),
        payload_for_friend=_ws_gift_payload(gift, friend_view, "friend"),
        payload_for_public=_ws_gift_payload(gift, public_view, "public"),
    )

    return owner_view


@router.delete("/gifts/{gift_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gift(
    gift_id: int,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> None:
    gift_result = await db.execute(select(Gift).where(Gift.id == gift_id))
    gift = gift_result.scalar_one_or_none()
    if not gift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found")

    await db.refresh(gift, attribute_names=["reservation", "contributions", "wishlist"])

    if gift.wishlist.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can delete gift")

    if gift.reservation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete gift with active reservation",
        )

    if gift.contributions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete gift with active contributions",
        )

    from app.models.models import WishlistItemArchive
    gift.is_unavailable = True
    gift.unavailable_reason = "Этот товар был удален из каталога"
    archive = WishlistItemArchive(
        wishlist_id=gift.wishlist_id,
        gift_id=gift.id,
        title=gift.title,
        image_url=gift.image_url,
        last_price=gift.price,
        reason=gift.unavailable_reason,
    )
    db.add(archive)
    await db.commit()

    try:
        from app.core.mailer import send_unavailable_gift_notice
        owner_result = await db.execute(select(User).where(User.id == gift.wishlist.owner_id))
        owner = owner_result.scalar_one_or_none()
        if owner and owner.email:
            send_unavailable_gift_notice(owner.email, gift.wishlist.title, gift.title)
    except Exception:
        pass

    contributions_total_result = await db.execute(
        select(func.coalesce(func.sum(Contribution.amount), 0)).where(Contribution.gift_id == gift.id)
    )
    total_contributions = float(contributions_total_result.scalar_one())

    owner_view = _serialize_gift(gift, total_contributions=total_contributions, viewer_role="owner")
    friend_view = _serialize_gift(gift, total_contributions=total_contributions, viewer_role="friend")
    public_view = _serialize_gift(gift, total_contributions=total_contributions, viewer_role="public")

    await manager.broadcast_gift_event(
        gift.wishlist.slug,
        event_type="gift_archived",
        payload_for_owner=_ws_gift_payload(gift, owner_view, "owner"),
        payload_for_friend=_ws_gift_payload(gift, friend_view, "friend"),
        payload_for_public=_ws_gift_payload(gift, public_view, "public"),
    )


@router.post("/gifts/{gift_id}/cancel-contribution", response_model=GiftPublic)
async def cancel_contribution(
    gift_id: int,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> GiftPublic:
    gift_result = await db.execute(select(Gift).where(Gift.id == gift_id))
    gift = gift_result.scalar_one_or_none()
    if not gift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found")

    await db.refresh(gift, attribute_names=["reservation", "contributions", "wishlist"])

    if not gift.is_collective:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gift is not collective",
        )

    # Find user's contributions. A user may have multiple partial contributions.
    contribution_result = await db.execute(
        select(Contribution).where(
            (Contribution.gift_id == gift_id) & (Contribution.user_id == current_user.id)
        ).order_by(Contribution.created_at.asc())
    )
    contributions = list(contribution_result.scalars().all())
    
    if not contributions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no contribution to this gift",
        )

    # Check if gift is already fully collected
    contributions_total_result = await db.execute(
        select(func.coalesce(func.sum(Contribution.amount), 0)).where(Contribution.gift_id == gift.id)
    )
    total_before = float(contributions_total_result.scalar_one())

    if total_before >= float(gift.price or 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel contribution - gift already fully collected",
        )

    for contribution in contributions:
        await db.delete(contribution)
    await db.commit()
    await db.refresh(gift, attribute_names=["reservation", "contributions", "wishlist"])

    contributions_total_result = await db.execute(
        select(func.coalesce(func.sum(Contribution.amount), 0)).where(Contribution.gift_id == gift.id)
    )
    total_contributions = float(contributions_total_result.scalar_one())

    viewer_role = "owner" if gift.wishlist.owner_id == current_user.id else "friend"

    owner_view = _serialize_gift(gift, total_contributions=total_contributions, viewer_role="owner")
    friend_view = _serialize_gift(gift, total_contributions=total_contributions, viewer_role="friend")
    public_view = _serialize_gift(gift, total_contributions=total_contributions, viewer_role="public")

    await manager.broadcast_gift_event(
        gift.wishlist.slug,
        event_type="contribution_canceled",
        payload_for_owner=_ws_gift_payload(gift, owner_view, "owner"),
        payload_for_friend=_ws_gift_payload(gift, friend_view, "friend"),
        payload_for_public=_ws_gift_payload(gift, public_view, "public"),
    )

    return _serialize_gift(
        gift,
        total_contributions=total_contributions,
        viewer_role=viewer_role,
        is_secret_santa=gift.wishlist.is_secret_santa,
    )


class ReserveGiftCompatRequest(BaseModel):
    amount: float | None = None


@compat_router.put("/gifts/{gift_id}", response_model=GiftPublic)
async def update_gift_compat(
    gift_id: int,
    payload: GiftUpdate,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> GiftPublic:
    return await update_gift(
        gift_id=gift_id,
        payload=payload,
        db=db,
        current_user=current_user,
    )


@compat_router.delete("/gifts/{gift_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gift_compat(
    gift_id: int,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> None:
    await delete_gift(
        gift_id=gift_id,
        db=db,
        current_user=current_user,
    )


@compat_router.post("/gifts/{gift_id}/reserve", response_model=GiftPublic)
async def reserve_gift_compat(
    gift_id: int,
    db: DbSessionDep,
    payload: ReserveGiftCompatRequest | None = Body(default=None),
    current_user: User = Depends(get_current_user),
) -> GiftPublic:
    gift_result = await db.execute(select(Gift).where(Gift.id == gift_id))
    gift = gift_result.scalar_one_or_none()
    if not gift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found")

    if gift.is_collective:
        if payload is None or payload.amount is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount is required for collective gift",
            )
        return await contribute_to_gift(
            payload=ContributionCreate(amount=payload.amount),
            gift_id=gift_id,
            db=db,
            current_user=current_user,
        )

    return await reserve_gift(gift_id=gift_id, db=db, current_user=current_user)


@compat_router.post("/gifts/{gift_id}/cancel-reservation", response_model=GiftPublic)
async def cancel_reservation_compat(
    gift_id: int,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> GiftPublic:
    return await cancel_reservation(gift_id=gift_id, db=db, current_user=current_user)


@compat_router.post("/gifts/{gift_id}/contribute", response_model=GiftPublic)
async def contribute_to_gift_compat(
    gift_id: int,
    payload: ContributionCreate,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> GiftPublic:
    return await contribute_to_gift(
        payload=payload,
        gift_id=gift_id,
        db=db,
        current_user=current_user,
    )


@compat_router.post("/gifts/{gift_id}/cancel-contribution", response_model=GiftPublic)
async def cancel_contribution_compat(
    gift_id: int,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> GiftPublic:
    return await cancel_contribution(gift_id=gift_id, db=db, current_user=current_user)


@compat_router.delete("/reservations/{reservation_id}", response_model=GiftPublic)
async def cancel_reservation_by_id_compat(
    reservation_id: int,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> GiftPublic:
    reservation_result = await db.execute(
        select(Reservation).where(Reservation.id == reservation_id)
    )
    reservation = reservation_result.scalar_one_or_none()
    if reservation:
        return await cancel_reservation(
            gift_id=reservation.gift_id,
            db=db,
            current_user=current_user,
        )

    contribution_result = await db.execute(
        select(Contribution).where(Contribution.id == reservation_id)
    )
    contribution = contribution_result.scalar_one_or_none()
    if contribution:
        return await cancel_contribution(
            gift_id=contribution.gift_id,
            db=db,
            current_user=current_user,
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Reservation not found",
    )
