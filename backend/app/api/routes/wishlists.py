from datetime import datetime, timezone
from typing import Annotated, Any
from time import perf_counter
import asyncio
import logging
import re

from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.api.deps import DbSessionDep, get_current_user, get_optional_user
from app.core.config import settings
from app.models.models import Contribution, Gift, PrivacyLevelEnum, Reservation, User, Wishlist, WishlistAccessEmail, WishlistDonation, WishlistItemArchive
from app.realtime.manager import manager

logger = logging.getLogger("wishshare.wishlists")

wishlist_cache = None
wishlist_metrics = None
send_gift_reserved_email = None
send_gift_unreserved_email = None
send_contribution_email = None

try:
    from app.core.wishlist_cache import wishlist_cache
except Exception as e:
    logger.warning("wishlist_cache import failed: %s", e)

try:
    from app.core.wishlist_metrics import wishlist_metrics
except Exception as e:
    logger.warning("wishlist_metrics import failed: %s", e)

try:
    from app.core.mailer import (
        send_gift_reserved_email,
        send_gift_unreserved_email,
        send_contribution_email,
    )
except Exception as e:
    logger.warning("mailer import failed: %s", e)

from app.schemas.wishlist import (
    ContributionCreate,
    ContributionPublic,
    GiftBase,
    GiftPublic,
    GiftUpdate,
    ReservationPublic,
    WishlistCreate,
    WishlistPublic,
    WishlistUpdate,
)

router = APIRouter(prefix="/wishlists", tags=["wishlists"])
compat_router = APIRouter(tags=["wishlists"])


def _record_list(duration_ms: float, cached: bool, error: bool) -> None:
    if wishlist_metrics:
        wishlist_metrics.record_list(duration_ms, cached, error)


def _record_item(duration_ms: float, cached: bool, error: bool) -> None:
    if wishlist_metrics:
        wishlist_metrics.record_item(duration_ms, cached, error)


async def _get_cached_list(user_id: int, limit: int, offset: int):
    if wishlist_cache:
        try:
            return await wishlist_cache.get_list(user_id, limit, offset)
        except Exception:
            logger.exception("wishlist_cache.get_list failed")
            return None
    return None


async def _set_cached_list(user_id: int, limit: int, offset: int, data: list) -> bool:
    if wishlist_cache:
        try:
            return await wishlist_cache.set_list(user_id, limit, offset, data)
        except Exception:
            logger.exception("wishlist_cache.set_list failed")
            return False
    return False


async def _get_cached_item(slug: str, role: str):
    if wishlist_cache:
        try:
            return await wishlist_cache.get_item(slug, role)
        except Exception:
            logger.exception("wishlist_cache.get_item failed")
            return None
    return None


async def _set_cached_item(slug: str, role: str, data: dict) -> bool:
    if wishlist_cache:
        try:
            return await wishlist_cache.set_item(slug, role, data)
        except Exception:
            logger.exception("wishlist_cache.set_item failed")
            return False
    return False


async def _invalidate_wishlist(slug: str) -> None:
    if wishlist_cache:
        try:
            await wishlist_cache.invalidate_wishlist(slug)
        except Exception:
            logger.exception("wishlist_cache.invalidate_wishlist failed")


async def _invalidate_lists(user_id: int) -> None:
    if wishlist_cache:
        try:
            await wishlist_cache.invalidate_lists(user_id)
        except Exception:
            logger.exception("wishlist_cache.invalidate_lists failed")


def _wishlist_fallback(
    wishlist: Wishlist,
    *,
    viewer_is_owner: bool = False,
    access_emails: list[str] | None = None,
) -> WishlistPublic:
    """Return a minimal WishlistPublic when full loading fails, avoiding code duplication."""
    safe_access_emails: list[str] = []
    if viewer_is_owner:
        if access_emails is not None:
            safe_access_emails = [email for email in access_emails if email]
        else:
            # Avoid triggering SQLAlchemy lazy-loading in fallback path (MissingGreenlet).
            preloaded_access = getattr(wishlist, "__dict__", {}).get("access_emails", [])
            if preloaded_access:
                for item in preloaded_access:
                    if isinstance(item, str):
                        safe_access_emails.append(item)
                    else:
                        value = getattr(item, "email", None)
                        if value:
                            safe_access_emails.append(value)

    return WishlistPublic(
        id=wishlist.id,
        slug=wishlist.slug,
        title=wishlist.title,
        description=wishlist.description,
        event_date=wishlist.event_date,
        privacy=wishlist.privacy,
        is_secret_santa=wishlist.is_secret_santa,
        created_at=wishlist.created_at,
        owner_id=wishlist.owner_id,
        gifts=[],
        access_emails=safe_access_emails,
        public_token=wishlist.public_token if viewer_is_owner else None,
    )


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


async def _load_wishlist_with_gifts_legacy(
    db: AsyncSession,
    wishlist: Wishlist,
    viewer: User | None,
) -> WishlistPublic:
    # Legacy loader: refreshes relationships per gift (may cause N queries)
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


async def _load_wishlist_with_gifts(
    db: AsyncSession,
    wishlist: Wishlist,
    viewer: User | None,
) -> WishlistPublic:
    """
    Optimized loader: performs a fixed number of batched queries and avoids per-gift refresh.
    Queries:
      1) gifts for wishlist
      2) contribution sums per gift
      3) reservations for gifts
      4) detailed contributions (only for 'friend' role)
      5) users referenced by reservations/contributions (if any)
      6) access emails (only when viewer is owner)
    """
    logger.debug("batched_loader: start wishlist_id=%s slug=%s", wishlist.id, wishlist.slug)

    viewer_role = "public"
    if viewer and viewer.id == wishlist.owner_id:
        viewer_role = "owner"
    elif viewer:
        viewer_role = "friend"
    logger.debug("batched_loader: viewer_role=%s", viewer_role)
    start_time = perf_counter()

    from sqlalchemy.orm import selectinload
    step_start = perf_counter()
    load_options = [selectinload(Gift.reservation)]
    need_contrib_detail = viewer_role == "friend"
    if need_contrib_detail:
        load_options.append(selectinload(Gift.contributions))
    wl_gifts_result = await db.execute(
        select(Gift)
        .options(*load_options)
        .where(Gift.wishlist_id == wishlist.id)
        .order_by(Gift.created_at.asc())
    )
    gifts: list[Gift] = list(wl_gifts_result.scalars().unique())
    gift_ids = [g.id for g in gifts]
    gifts_ms = (perf_counter() - step_start) * 1000.0
    logger.debug("batched_loader: found %d gifts duration_ms=%.2f", len(gifts), gifts_ms)

    contributions_map: dict[int, float] = {}
    step_start = perf_counter()
    if gift_ids:
        contrib_sum_result = await db.execute(
            select(
                Contribution.gift_id,
                func.coalesce(func.sum(Contribution.amount), 0),
            )
            .where(Contribution.gift_id.in_(gift_ids))
            .group_by(Contribution.gift_id)
        )
        contributions_map = {row[0]: float(row[1]) for row in contrib_sum_result.all()}
    contrib_ms = (perf_counter() - step_start) * 1000.0
    logger.debug("batched_loader: contribution sums for %d gifts duration_ms=%.2f", len(contributions_map), contrib_ms)

    step_start = perf_counter()
    user_ids: set[int] = set()
    for g in gifts:
        if g.reservation:
            user_ids.add(g.reservation.user_id)
        if need_contrib_detail:
            for c in g.contributions:
                user_ids.add(c.user_id)
    user_lookup: dict[int, User] = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        user_lookup = {u.id: u for u in users_result.scalars().unique()}
    users_ms = (perf_counter() - step_start) * 1000.0
    logger.debug("batched_loader: users loaded=%d duration_ms=%.2f", len(user_lookup), users_ms)

    step_start = perf_counter()
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
    serialize_ms = (perf_counter() - step_start) * 1000.0
    logger.debug("batched_loader: serialized %d gifts duration_ms=%.2f", len(gift_public_list), serialize_ms)

    step_start = perf_counter()
    access_emails: list[str] = []
    if viewer_role == "owner":
        ae_result = await db.execute(
            select(WishlistAccessEmail.email)
            .where(WishlistAccessEmail.wishlist_id == wishlist.id)
            .order_by(WishlistAccessEmail.email.asc())
        )
        access_emails = [row[0] for row in ae_result.all() if row[0]]
    access_ms = (perf_counter() - step_start) * 1000.0
    logger.debug("batched_loader: access_emails=%d duration_ms=%.2f", len(access_emails), access_ms)

    # Normalize privacy to enum
    privacy_value = wishlist.privacy
    if isinstance(privacy_value, str):
        try:
            privacy_value = PrivacyLevelEnum(privacy_value)
        except ValueError:
            pass

    total_ms = (perf_counter() - start_time) * 1000.0
    logger.info(
        "batched_loader: done wishlist_id=%s role=%s gifts=%d total_ms=%.2f",
        wishlist.id,
        viewer_role,
        len(gift_public_list),
        total_ms,
    )
    return WishlistPublic(
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


async def _load_wishlist_with_gifts_retry(
    db: AsyncSession,
    wishlist: Wishlist,
    viewer: User | None,
) -> WishlistPublic:
    attempts = 0
    while True:
        try:
            return await _load_wishlist_with_gifts(db, wishlist, viewer)
        except Exception:
            attempts += 1
            if attempts >= 2:
                raise
            await asyncio.sleep(0.05 * 2 ** (attempts - 1))


async def _invalidate_wishlist_cache(wishlist: Wishlist) -> None:
    if wishlist_cache:
        await wishlist_cache.invalidate_wishlist(wishlist.slug)
        await wishlist_cache.invalidate_lists(wishlist.owner_id)


async def _has_friends_access(db: AsyncSession, wishlist: Wishlist, viewer: User | None) -> bool:
    if not viewer:
        return False
    if viewer.id == wishlist.owner_id:
        return True
    normalized = (viewer.email or "").strip().lower()
    if not normalized:
        return False
    access_result = await db.execute(
        select(WishlistAccessEmail.id)
        .where(WishlistAccessEmail.wishlist_id == wishlist.id)
        .where(func.lower(WishlistAccessEmail.email) == normalized)
        .limit(1)
    )
    return access_result.scalar_one_or_none() is not None


def _slugify(title: str) -> str:
    slug = title.strip().lower()
    slug = re.sub(r"[^a-z0-9а-яё]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "wishlist"


@router.get("", response_model=list[WishlistPublic])
@router.get("/my", response_model=list[WishlistPublic])
async def list_my_wishlists(
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
) -> list[WishlistPublic]:
    """
    Return wishlists owned by the current user (paginated).

    Query params:
      limit  – max items to return (default 50, max 100)
      offset – skip first N wishlists (for pagination)

    Uses a batch-load strategy: 7 fixed queries total, regardless of list size.
    """
    start_time = perf_counter()
    limit = min(max(1, limit), 100)
    offset = max(0, offset)

    cached_list = await _get_cached_list(current_user.id, limit, offset)
    if cached_list:
        duration_ms = (perf_counter() - start_time) * 1000.0
        if wishlist_metrics:
            _record_list(duration_ms, cached=True, error=False)
        if duration_ms >= settings.wishlist_slow_ms:
            logger.warning("list_my_wishlists slow cache user_id=%s duration_ms=%.2f", current_user.id, duration_ms)
        return [WishlistPublic.model_validate(item) for item in cached_list]

    logger.info("list_my_wishlists: starting for user_id=%s limit=%s offset=%s", current_user.id, limit, offset)

    # ── 1. Wishlists ────────────────────────────────────────────────────────
    try:
        wl_result = await db.execute(
            select(Wishlist)
            .where(Wishlist.owner_id == current_user.id)
            .order_by(Wishlist.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        wishlists = list(wl_result.scalars().unique())
    except Exception:
        logger.exception("list_my_wishlists: DB query failed for user_id=%s", current_user.id)
        duration_ms = (perf_counter() - start_time) * 1000.0
        if wishlist_metrics:
            _record_list(duration_ms, cached=False, error=True)
        duration_ms = (perf_counter() - start_time) * 1000.0
        if wishlist_metrics:
            _record_list(duration_ms, cached=False, error=False)
        return []

    wishlist_ids = [w.id for w in wishlists]
    wishlist_map: dict[int, Wishlist] = {w.id: w for w in wishlists}

    # ── 2. All gifts ─────────────────────────────────────────────────────────
    gifts_result = await db.execute(
        select(Gift)
        .where(Gift.wishlist_id.in_(wishlist_ids))
        .order_by(Gift.created_at.asc())
    )
    all_gifts: list[Gift] = list(gifts_result.scalars().unique())
    gift_ids = [g.id for g in all_gifts]

    # gifts grouped by wishlist
    gifts_by_wl: dict[int, list[Gift]] = {wid: [] for wid in wishlist_ids}
    for g in all_gifts:
        gifts_by_wl[g.wishlist_id].append(g)

    # ── 3. Contribution sums per gift ────────────────────────────────────────
    contributions_map: dict[int, float] = {}
    if gift_ids:
        contrib_sum_result = await db.execute(
            select(
                Contribution.gift_id,
                func.coalesce(func.sum(Contribution.amount), 0),
            )
            .where(Contribution.gift_id.in_(gift_ids))
            .group_by(Contribution.gift_id)
        )
        contributions_map = {row[0]: float(row[1]) for row in contrib_sum_result.all()}

    # ── 4. Reservations ──────────────────────────────────────────────────────
    reservation_map: dict[int, Reservation] = {}  # gift_id → Reservation
    if gift_ids:
        res_result = await db.execute(
            select(Reservation).where(Reservation.gift_id.in_(gift_ids))
        )
        for rsv in res_result.scalars().unique():
            reservation_map[rsv.gift_id] = rsv

    contrib_by_gift: dict[int, list[Contribution]] = {gid: [] for gid in gift_ids}
    user_lookup: dict[int, User] = {}

    access_emails_by_wl: dict[int, list[str]] = {wid: [] for wid in wishlist_ids}
    ae_result = await db.execute(
        select(WishlistAccessEmail)
        .where(WishlistAccessEmail.wishlist_id.in_(wishlist_ids))
        .order_by(WishlistAccessEmail.email.asc())
    )
    for ae in ae_result.scalars().unique():
        if ae.email:
            access_emails_by_wl[ae.wishlist_id].append(ae.email)

    # ── Assemble results ─────────────────────────────────────────────────────
    result_list: list[WishlistPublic] = []
    for wishlist in wishlists:
        try:
            # Owner always sees everything for their own wishlists
            viewer_role = "owner"
            wl_gifts = gifts_by_wl.get(wishlist.id, [])

            # Attach relationships to gift objects in-memory (no extra DB calls)
            for gift in wl_gifts:
                gift.reservation = reservation_map.get(gift.id)  # type: ignore[assignment]
                gift.contributions = []  # type: ignore[assignment]

            privacy_value = wishlist.privacy
            if isinstance(privacy_value, str):
                try:
                    privacy_value = PrivacyLevelEnum(privacy_value)
                except ValueError:
                    pass

            gift_public_list = [
                _serialize_gift(
                    gift,
                    contributions_map.get(gift.id, 0.0),
                    viewer_role=viewer_role,
                    user_lookup=user_lookup,
                    is_secret_santa=wishlist.is_secret_santa,
                )
                for gift in wl_gifts
            ]

            result_list.append(WishlistPublic(
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
                access_emails=access_emails_by_wl.get(wishlist.id, []),
                public_token=wishlist.public_token,
            ))
        except Exception:
            logger.exception(
                "list_my_wishlists: failed to serialize wishlist id=%s slug=%s",
                wishlist.id, wishlist.slug,
            )
            result_list.append(
                _wishlist_fallback(
                    wishlist,
                    viewer_is_owner=True,
                    access_emails=access_emails_by_wl.get(wishlist.id, []),
                )
            )

    await _set_cached_list(
        current_user.id,
        limit,
        offset,
        [wishlist.model_dump() for wishlist in result_list],
    )
    duration_ms = (perf_counter() - start_time) * 1000.0
    _record_list(duration_ms, cached=False, error=False)
    if duration_ms >= settings.wishlist_slow_ms:
        logger.warning("list_my_wishlists slow user_id=%s duration_ms=%.2f", current_user.id, duration_ms)
    logger.info("list_my_wishlists: returned %d wishlists for user_id=%s", len(result_list), current_user.id)
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
    await _invalidate_wishlist_cache(wishlist)
    
    try:
        return await _load_wishlist_with_gifts_retry(db, wishlist, current_user)
    except Exception as e:
        logger.exception("update_wishlist: failed to load wishlist after update: %s", str(e))
        return _wishlist_fallback(
            wishlist,
            viewer_is_owner=True,
            access_emails=normalized_emails,
        )


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
    await _invalidate_wishlist_cache(wishlist)


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
        created_at=datetime.now(timezone.utc),
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
    await _invalidate_wishlist_cache(wishlist)
    
    try:
        return await _load_wishlist_with_gifts_retry(db, wishlist, current_user)
    except Exception as e:
        logger.exception("create_wishlist: failed to load wishlist after creation: %s", str(e))
        return _wishlist_fallback(wishlist, viewer_is_owner=True)


@router.get("/token/{token}", response_model=WishlistPublic)
async def get_wishlist_by_token(
    token: str,
    db: DbSessionDep,
    response: Response,
) -> WishlistPublic:
    start_time = perf_counter()
    result = await db.execute(select(Wishlist).where(Wishlist.public_token == token))
    wishlist = result.scalar_one_or_none()
    if not wishlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist not found")

    if wishlist.privacy not in ("public", "link_only"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    response.headers["Cache-Control"] = "public, max-age=60"

    try:
        cached = await _get_cached_item(wishlist.slug, "public")
        if cached:
            duration_ms = (perf_counter() - start_time) * 1000.0
            _record_item(duration_ms, cached=True, error=False)
            if duration_ms >= settings.wishlist_slow_ms:
                logger.warning("get_wishlist_by_token slow cache token=%s duration_ms=%.2f", token, duration_ms)
            return WishlistPublic.model_validate(cached)
        result = await _load_wishlist_with_gifts_retry(db, wishlist, None)
        await _set_cached_item(wishlist.slug, "public", result.model_dump())
        duration_ms = (perf_counter() - start_time) * 1000.0
        _record_item(duration_ms, cached=False, error=False)
        if duration_ms >= settings.wishlist_slow_ms:
            logger.warning("get_wishlist_by_token slow token=%s duration_ms=%.2f", token, duration_ms)
        return result
    except Exception as e:
        logger.exception("get_wishlist_by_token: failed to load wishlist: %s", str(e))
        duration_ms = (perf_counter() - start_time) * 1000.0
        _record_item(duration_ms, cached=False, error=True)
        return _wishlist_fallback(wishlist)


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
    await _invalidate_wishlist_cache(wishlist)
    return {"public_token": wishlist.public_token}


@router.get("/{slug}", response_model=WishlistPublic)
async def get_wishlist_by_slug(
    slug: str,
    db: DbSessionDep,
    viewer: User | None = Depends(get_optional_user),
) -> WishlistPublic:
    start_time = perf_counter()
    result = await db.execute(select(Wishlist).where(Wishlist.slug == slug))
    wishlist = result.scalar_one_or_none()
    if not wishlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist not found")

    viewer_is_owner = viewer is not None and viewer.id == wishlist.owner_id

    if wishlist.privacy in ("public", "link_only"):
        try:
            role = "owner" if viewer_is_owner else ("friend" if viewer else "public")
            cached = await _get_cached_item(wishlist.slug, role)
            if cached:
                duration_ms = (perf_counter() - start_time) * 1000.0
                _record_item(duration_ms, cached=True, error=False)
                if duration_ms >= settings.wishlist_slow_ms:
                    logger.warning("get_wishlist_by_slug slow cache slug=%s duration_ms=%.2f", slug, duration_ms)
                return WishlistPublic.model_validate(cached)
            result = await _load_wishlist_with_gifts_retry(db, wishlist, viewer)
            await _set_cached_item(wishlist.slug, role, result.model_dump())
            duration_ms = (perf_counter() - start_time) * 1000.0
            _record_item(duration_ms, cached=False, error=False)
            if duration_ms >= settings.wishlist_slow_ms:
                logger.warning("get_wishlist_by_slug slow slug=%s duration_ms=%.2f", slug, duration_ms)
            return result
        except Exception as e:
            logger.exception("get_wishlist_by_slug: failed to load wishlist: %s", str(e))
            duration_ms = (perf_counter() - start_time) * 1000.0
            _record_item(duration_ms, cached=False, error=True)
            return _wishlist_fallback(wishlist, viewer_is_owner=viewer_is_owner)

    if not viewer:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    if wishlist.privacy == "friends":
        has_access = await _has_friends_access(db, wishlist, viewer)
        if not has_access:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        try:
            cached = await _get_cached_item(wishlist.slug, "friend")
            if cached:
                duration_ms = (perf_counter() - start_time) * 1000.0
                _record_item(duration_ms, cached=True, error=False)
                if duration_ms >= settings.wishlist_slow_ms:
                    logger.warning("get_wishlist_by_slug slow cache slug=%s duration_ms=%.2f", slug, duration_ms)
                return WishlistPublic.model_validate(cached)
            result = await _load_wishlist_with_gifts_retry(db, wishlist, viewer)
            await _set_cached_item(wishlist.slug, "friend", result.model_dump())
            duration_ms = (perf_counter() - start_time) * 1000.0
            _record_item(duration_ms, cached=False, error=False)
            if duration_ms >= settings.wishlist_slow_ms:
                logger.warning("get_wishlist_by_slug slow slug=%s duration_ms=%.2f", slug, duration_ms)
            return result
        except Exception as e:
            logger.exception("get_wishlist_by_slug: failed to load wishlist: %s", str(e))
            duration_ms = (perf_counter() - start_time) * 1000.0
            _record_item(duration_ms, cached=False, error=True)
            return _wishlist_fallback(wishlist, viewer_is_owner=viewer_is_owner)

    try:
        role = "owner" if viewer_is_owner else ("friend" if viewer else "public")
        cached = await _get_cached_item(wishlist.slug, role)
        if cached:
            duration_ms = (perf_counter() - start_time) * 1000.0
            _record_item(duration_ms, cached=True, error=False)
            if duration_ms >= settings.wishlist_slow_ms:
                logger.warning("get_wishlist_by_slug slow cache slug=%s duration_ms=%.2f", slug, duration_ms)
            return WishlistPublic.model_validate(cached)
        result = await _load_wishlist_with_gifts_retry(db, wishlist, viewer)
        await _set_cached_item(wishlist.slug, role, result.model_dump())
        duration_ms = (perf_counter() - start_time) * 1000.0
        _record_item(duration_ms, cached=False, error=False)
        if duration_ms >= settings.wishlist_slow_ms:
            logger.warning("get_wishlist_by_slug slow slug=%s duration_ms=%.2f", slug, duration_ms)
        return result
    except Exception as e:
        logger.exception("get_wishlist_by_slug: failed to load wishlist: %s", str(e))
        duration_ms = (perf_counter() - start_time) * 1000.0
        _record_item(duration_ms, cached=False, error=True)
        return _wishlist_fallback(wishlist, viewer_is_owner=viewer_is_owner)


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
    await _invalidate_wishlist_cache(wishlist)

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
    await _invalidate_wishlist_cache(gift.wishlist)

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

    # Send email notification to wishlist owner
    if settings.email_notifications_enabled:
        try:
            owner_result = await db.execute(select(User).where(User.id == gift.wishlist.owner_id))
            owner = owner_result.scalar_one_or_none()
            if owner and owner.email:
                wishlist_link = f"{settings.frontend_url}/wishlist/{gift.wishlist.slug}"
                send_gift_reserved_email(
                    to_email=owner.email,
                    gift_title=gift.title,
                    wishlist_title=gift.wishlist.title,
                    wishlist_link=wishlist_link,
                    reserved_by_name=current_user.name if not gift.wishlist.is_secret_santa else None,
                    is_secret_santa=gift.wishlist.is_secret_santa,
                )
        except Exception as e:
            logger.warning("Failed to send reservation notification email: %s", e)

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
    await _invalidate_wishlist_cache(gift.wishlist)

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

    # Send email notification to wishlist owner
    if settings.email_notifications_enabled:
        try:
            owner_result = await db.execute(select(User).where(User.id == gift.wishlist.owner_id))
            owner = owner_result.scalar_one_or_none()
            if owner and owner.email:
                wishlist_link = f"{settings.frontend_url}/wishlist/{gift.wishlist.slug}"
                send_gift_unreserved_email(
                    to_email=owner.email,
                    gift_title=gift.title,
                    wishlist_title=gift.wishlist.title,
                    wishlist_link=wishlist_link,
                )
        except Exception as e:
            logger.warning("Failed to send unreserve notification email: %s", e)

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
        donation = WishlistDonation(
            wishlist_id=gift.wishlist_id,
            gift_id=gift.id,
            user_id=current_user.id,
            amount=payload.amount,
        )
        db.add(donation)
    except Exception as e:
        # FIX: Log the error instead of silently ignoring it
        logger.warning(
            "Failed to add donation record for gift_id=%s user_id=%s amount=%s: %s",
            gift.id,
            current_user.id,
            payload.amount,
            str(e),
        )
    await db.commit()
    await db.refresh(gift, attribute_names=["reservation", "contributions", "wishlist"])
    await _invalidate_wishlist_cache(gift.wishlist)

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

    # Send email notification to wishlist owner
    if settings.email_notifications_enabled:
        try:
            owner_result = await db.execute(select(User).where(User.id == gift.wishlist.owner_id))
            owner = owner_result.scalar_one_or_none()
            if owner and owner.email:
                wishlist_link = f"{settings.frontend_url}/wishlist/{gift.wishlist.slug}"
                send_contribution_email(
                    to_email=owner.email,
                    gift_title=gift.title,
                    wishlist_title=gift.wishlist.title,
                    wishlist_link=wishlist_link,
                    contribution_amount=float(payload.amount),
                    total_collected=total_contributions,
                    target_amount=float(gift.price) if gift.price else 0.0,
                    contributor_name=current_user.name if not gift.wishlist.is_secret_santa else None,
                    is_secret=gift.wishlist.is_secret_santa,
                )
        except Exception as e:
            logger.warning("Failed to send contribution notification email: %s", e)

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
    await _invalidate_wishlist_cache(gift.wishlist)

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
    await _invalidate_wishlist_cache(gift.wishlist)

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
    await _invalidate_wishlist_cache(gift.wishlist)

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
