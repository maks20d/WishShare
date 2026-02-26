from datetime import datetime, timezone

from app.api.routes.wishlists import _wishlist_fallback
from app.models.models import PrivacyLevelEnum


class _WishlistWithLazyAccessEmails:
    id = 1
    slug = "test-slug"
    title = "Test"
    description = None
    event_date = None
    privacy = PrivacyLevelEnum.LINK_ONLY
    is_secret_santa = False
    created_at = datetime.now(timezone.utc)
    owner_id = 10
    public_token = "public-token"

    @property
    def access_emails(self):  # pragma: no cover - should never be called
        raise RuntimeError("Lazy load attempted")


def test_wishlist_fallback_does_not_trigger_lazy_access_emails():
    wishlist = _WishlistWithLazyAccessEmails()

    result = _wishlist_fallback(wishlist, viewer_is_owner=True)

    assert result.id == wishlist.id
    assert result.access_emails == []
    assert result.public_token == wishlist.public_token
