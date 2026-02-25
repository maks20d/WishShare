from urllib.parse import urlencode, urlparse
import secrets
from typing import TypedDict

import httpx
import logging
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSessionDep, get_current_user
from app.core.mailer import send_email_verification_email, send_password_reset_email
from app.core.config import settings
from app.core.rate_limit import check_rate_limit
from app.core.audit import (
    audit_login_success,
    audit_login_failed,
    audit_logout,
    audit_register,
    audit_password_change,
    audit_password_reset_request,
    audit_oauth_login,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_email_verification_token,
    create_password_reset_token,
    decode_email_verification_token,
    decode_password_reset_token,
    decode_refresh_token,
    get_password_hash,
    verify_password,
)
from app.models.models import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserPublic,
    UserUpdate,
    ChangePasswordRequest,
)


router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("wishshare")


class CookieOptions(TypedDict, total=False):
    """Type-safe cookie options for cross-origin authentication."""
    samesite: str
    secure: bool


DEFAULT_SESSION_DAYS = 30
ALLOWED_SESSION_DAYS = {7, 30}


def _cookie_options() -> CookieOptions:
    """
    Return cookie options based on environment.
    
    For cross-origin authentication (frontend on Vercel, backend on Render):
    - samesite="none" - required for cross-origin requests
    - secure=True - required for HTTPS (Render uses HTTPS)
    - NO domain - cookie must NOT be tied to a specific domain for cross-origin
    
    For local development:
    - samesite="lax" - more secure, works for same-origin
    - secure=False - HTTP on localhost
    """
    environment = (settings.environment or "local").lower()
    if environment == "local":
        logger.debug("Cookie options: local mode (samesite=lax, secure=False)")
        return {"samesite": "lax", "secure": False}
    # Production: cross-origin cookies
    # DO NOT set domain - it breaks cross-origin cookie sending
    # Browser will send cookie to the backend URL that set it
    logger.info("Cookie options: production mode (samesite=none, secure=True)")
    return {"samesite": "none", "secure": True}


def _resolve_cookie_max_age(remember_me: bool, session_days: int | None) -> int | None:
    if not remember_me:
        return None
    days = session_days if session_days in ALLOWED_SESSION_DAYS else DEFAULT_SESSION_DAYS
    return days * 24 * 60 * 60


def _set_auth_cookie(
    response: Response,
    token: str,
    *,
    remember_me: bool = True,
    session_days: int | None = DEFAULT_SESSION_DAYS,
) -> None:
    response.set_cookie(
        "access_token",
        token,
        httponly=True,
        max_age=_resolve_cookie_max_age(remember_me, session_days),
        path="/",
        **_cookie_options(),
    )


def _set_refresh_cookie(
    response: Response,
    token: str,
    *,
    remember_me: bool = True,
    session_days: int | None = DEFAULT_SESSION_DAYS,
) -> None:
    response.set_cookie(
        "refresh_token",
        token,
        httponly=True,
        max_age=_resolve_cookie_max_age(remember_me, session_days),
        path="/",
        **_cookie_options(),
    )


def _set_session_prefs_cookie(
    response: Response,
    *,
    remember_me: bool,
    session_days: int | None,
) -> None:
    max_age = _resolve_cookie_max_age(remember_me, session_days)
    normalized_days = session_days if session_days in ALLOWED_SESSION_DAYS else DEFAULT_SESSION_DAYS
    response.set_cookie(
        "remember_me",
        "1" if remember_me else "0",
        httponly=True,
        max_age=max_age,
        path="/",
        **_cookie_options(),
    )
    response.set_cookie(
        "session_days",
        str(normalized_days),
        httponly=True,
        max_age=max_age,
        path="/",
        **_cookie_options(),
    )


def _parse_session_days(raw: str | None) -> int:
    try:
        parsed = int(raw or "")
    except ValueError:
        parsed = DEFAULT_SESSION_DAYS
    return parsed if parsed in ALLOWED_SESSION_DAYS else DEFAULT_SESSION_DAYS


def _safe_next_path(next_path: str | None) -> str:
    """Validate redirect path to prevent open redirect attacks.
    
    SECURITY: Blocks paths that could be interpreted as external URLs:
    - Paths starting with // (protocol-relative URLs)
    - Paths containing :// (absolute URLs with protocol)
    - Paths like /.evil.com that browsers may interpret as domain names
    """
    if not next_path:
        return "/dashboard"
    if not next_path.startswith("/") or next_path.startswith("//") or "://" in next_path:
        return "/dashboard"
    # SECURITY: Block paths that start with /. followed by domain-like patterns
    # This prevents redirects like /.evil.com which browsers may interpret as external
    if next_path.startswith("/.") and len(next_path) > 2 and "." in next_path[2:]:
        return "/dashboard"
    return next_path


def _build_oauth_redirect_response(
    user: User,
    next_path: str | None = None,
    clear_oauth_state_cookie: str | None = None,
    clear_oauth_next_cookie: str | None = None,
) -> RedirectResponse:
    token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    safe_next = _safe_next_path(next_path)
    response = RedirectResponse(url=f"{settings.frontend_url}{safe_next}", status_code=302)
    _set_auth_cookie(response, token)
    _set_refresh_cookie(response, refresh_token)
    _set_session_prefs_cookie(response, remember_me=True, session_days=DEFAULT_SESSION_DAYS)
    if clear_oauth_state_cookie:
        response.delete_cookie(clear_oauth_state_cookie, **_cookie_options())
    if clear_oauth_next_cookie:
        response.delete_cookie(clear_oauth_next_cookie, **_cookie_options())
    return response


async def _get_or_create_user_from_oauth(
    db: DbSessionDep,
    *,
    email: str,
    name: str,
    avatar_url: str | None = None,
) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        changed = False
        if name and user.name != name:
            user.name = name
            changed = True
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
            changed = True
        if not user.is_email_verified:
            user.is_email_verified = True
            changed = True
        if changed:
            await db.commit()
            await db.refresh(user)
        return user

    generated_password = secrets.token_urlsafe(24)
    user = User(
        email=email,
        hashed_password=get_password_hash(generated_password),
        name=name or email.split("@")[0],
        avatar_url=avatar_url,
        is_email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _validate_oauth_state(
    *,
    expected_state: str | None,
    provided_state: str | None,
) -> None:
    if not expected_state or not provided_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        )
    if not secrets.compare_digest(expected_state, provided_state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        )


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: RegisterRequest,
    db: DbSessionDep,
    request: Request,
    response: Response,
) -> UserPublic:
    # Rate limit registration to prevent spam
    check_rate_limit(request, max_requests=5, window_seconds=300, key_suffix="register")
    
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        return JSONResponse(status_code=status.HTTP_201_CREATED, content={})

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        name=payload.name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Issue auth cookies immediately — no second /login request needed
    _set_auth_cookie(
        response,
        create_access_token(str(user.id)),
        remember_me=payload.remember_me,
        session_days=payload.session_days,
    )
    _set_refresh_cookie(
        response,
        create_refresh_token(str(user.id)),
        remember_me=payload.remember_me,
        session_days=payload.session_days,
    )
    _set_session_prefs_cookie(
        response,
        remember_me=payload.remember_me,
        session_days=payload.session_days,
    )

    token = create_email_verification_token(user.email)
    verify_link = f"{settings.backend_url}/auth/verify-email?token={token}"
    send_email_verification_email(user.email, verify_link)
    audit_register(request, user.id, user.email)
    return UserPublic.model_validate(user)


@router.post("/login", response_model=UserPublic)
async def login_user(
    payload: LoginRequest,
    response: Response,
    db: DbSessionDep,
    request: Request,
) -> UserPublic:
    # Rate limit login to prevent brute force (5 attempts per minute)
    check_rate_limit(request, max_requests=settings.rate_limit_login_requests, window_seconds=60, key_suffix="login")
    
    request_id = request.headers.get("X-Request-Id")
    client_host = request.client.host if request.client else None
    logger.info(
        "Auth login request id=%s email=%s ip=%s ua=%s",
        request_id,
        payload.email,
        client_host,
        request.headers.get("user-agent"),
    )
    try:
        result = await db.execute(select(User).where(User.email == payload.email))
        user = result.scalar_one_or_none()
    except SQLAlchemyError:
        logger.exception(
            "Auth login db error id=%s email=%s ip=%s",
            request_id,
            payload.email,
            client_host,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    if not user:
        logger.info("Auth login user not found id=%s email=%s", request_id, payload.email)
        audit_login_failed(request, payload.email, "user_not_found")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь не найден. Зарегистрируйтесь.",
        )
    try:
        password_ok = verify_password(payload.password, user.hashed_password)
    except Exception:
        logger.exception(
            "Auth login verify failed id=%s user_id=%s",
            request_id,
            user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
    if not password_ok:
        logger.info("Auth login invalid password id=%s user_id=%s", request_id, user.id)
        audit_login_failed(request, payload.email, "invalid_password")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный пароль.",
        )

    token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    _set_auth_cookie(
        response,
        token,
        remember_me=payload.remember_me,
        session_days=payload.session_days,
    )
    _set_refresh_cookie(
        response,
        refresh_token,
        remember_me=payload.remember_me,
        session_days=payload.session_days,
    )
    _set_session_prefs_cookie(
        response,
        remember_me=payload.remember_me,
        session_days=payload.session_days,
    )
    audit_login_success(request, user.id, user.email)
    logger.info("Auth login success id=%s user_id=%s", request_id, user.id)
    return UserPublic.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_user(response: Response) -> None:
    response.delete_cookie("access_token", path="/", **_cookie_options())
    response.delete_cookie("refresh_token", path="/", **_cookie_options())
    response.delete_cookie("remember_me", path="/", **_cookie_options())
    response.delete_cookie("session_days", path="/", **_cookie_options())


@router.post("/refresh", status_code=status.HTTP_204_NO_CONTENT)
async def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="refresh_token"),
    remember_me_cookie: str | None = Cookie(default="1", alias="remember_me"),
    session_days_cookie: str | None = Cookie(default=str(DEFAULT_SESSION_DAYS), alias="session_days"),
) -> None:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_refresh_token(refresh_token)
    if not payload or "sub" not in payload:
        response.delete_cookie("refresh_token", path="/", **_cookie_options())
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    subject = payload.get("sub")
    if not isinstance(subject, str):
        response.delete_cookie("refresh_token", path="/", **_cookie_options())
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    new_access_token = create_access_token(subject)
    new_refresh_token = create_refresh_token(subject)
    remember_me = remember_me_cookie != "0"
    session_days = _parse_session_days(session_days_cookie)
    _set_auth_cookie(
        response,
        new_access_token,
        remember_me=remember_me,
        session_days=session_days,
    )
    _set_refresh_cookie(
        response,
        new_refresh_token,
        remember_me=remember_me,
        session_days=session_days,
    )
    _set_session_prefs_cookie(
        response,
        remember_me=remember_me,
        session_days=session_days,
    )


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.put("/me", response_model=UserPublic)
async def update_profile(
    payload: UserUpdate,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> UserPublic:
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(current_user, key):
            setattr(current_user, key, value)

    await db.commit()
    await db.refresh(current_user)
    return UserPublic.model_validate(current_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    db: DbSessionDep,
    current_user: User = Depends(get_current_user),
) -> None:
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password",
        )

    current_user.hashed_password = get_password_hash(payload.new_password)
    await db.commit()


@router.get("/verify-email")
async def verify_email(db: DbSessionDep, token: str = Query(...)) -> RedirectResponse:
    email = decode_email_verification_token(token)
    if not email:
        return RedirectResponse(url=f"{settings.frontend_url}/auth/login?verified=0", status_code=302)

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return RedirectResponse(url=f"{settings.frontend_url}/auth/login?verified=0", status_code=302)

    if not user.is_email_verified:
        user.is_email_verified = True
        await db.commit()

    return RedirectResponse(url=f"{settings.frontend_url}/auth/login?verified=1", status_code=302)


@router.get("/oauth/google")
async def oauth_google_login(next: str | None = Query(default=None)):
    """Get Google OAuth login URL."""
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth not configured",
        )
    
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": f"{settings.backend_url}/auth/oauth/callback/google",
        "response_type": "code",
        "scope": "openid profile email",
        "access_type": "offline",
        "prompt": "consent",
    }
    state = secrets.token_urlsafe(32)
    params["state"] = state
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    response = JSONResponse({"url": auth_url})
    response.set_cookie(
        "oauth_state_google",
        state,
        httponly=True,
        **_cookie_options(),
        max_age=600,
    )
    if next:
        response.set_cookie(
            "oauth_next",
            next,
            httponly=True,
            **_cookie_options(),
            max_age=600,
        )
    return response


@router.get("/oauth/github")
async def oauth_github_login(next: str | None = Query(default=None)):
    """Get GitHub OAuth login URL."""
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub OAuth not configured",
        )
    
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": f"{settings.backend_url}/auth/oauth/callback/github",
        "scope": "read:user user:email",
    }
    state = secrets.token_urlsafe(32)
    params["state"] = state
    auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"

    response = JSONResponse({"url": auth_url})
    response.set_cookie(
        "oauth_state_github",
        state,
        httponly=True,
        **_cookie_options(),
        max_age=600,
    )
    if next:
        response.set_cookie(
            "oauth_next",
            next,
            httponly=True,
            **_cookie_options(),
            max_age=600,
        )
    return response


@router.get("/oauth/callback/google")
async def oauth_google_callback(
    code: str,
    db: DbSessionDep,
    state: str | None = None,
    oauth_state_google: str | None = Cookie(default=None),
    oauth_next: str | None = Cookie(default=None),
):
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth not configured",
        )
    _validate_oauth_state(
        expected_state=oauth_state_google,
        provided_state=state,
    )

    token_payload = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": f"{settings.backend_url}/auth/oauth/callback/google",
        "grant_type": "authorization_code",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_res = await client.post(
                "https://oauth2.googleapis.com/token",
                data=token_payload,
            )
            token_res.raise_for_status()
            token_data = token_res.json()

            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="Google OAuth token is missing")

            user_res = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_res.raise_for_status()
            profile = user_res.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Google OAuth request failed: {exc}") from exc

    email = profile.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google OAuth email is missing")

    user = await _get_or_create_user_from_oauth(
        db,
        email=email,
        name=profile.get("name") or email.split("@")[0],
        avatar_url=profile.get("picture"),
    )
    return _build_oauth_redirect_response(
        user,
        next_path=oauth_next,
        clear_oauth_state_cookie="oauth_state_google",
        clear_oauth_next_cookie="oauth_next",
    )


@router.get("/oauth/callback/github")
async def oauth_github_callback(
    code: str,
    db: DbSessionDep,
    state: str | None = None,
    oauth_state_github: str | None = Cookie(default=None),
    oauth_next: str | None = Cookie(default=None),
):
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub OAuth not configured",
        )
    _validate_oauth_state(
        expected_state=oauth_state_github,
        provided_state=state,
    )

    token_payload = {
        "code": code,
        "client_id": settings.github_client_id,
        "client_secret": settings.github_client_secret,
        "redirect_uri": f"{settings.backend_url}/auth/oauth/callback/github",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_res = await client.post(
                "https://github.com/login/oauth/access_token",
                data=token_payload,
                headers={"Accept": "application/json"},
            )
            token_res.raise_for_status()
            token_data = token_res.json()

            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="GitHub OAuth token is missing")

            user_res = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            user_res.raise_for_status()
            profile = user_res.json()

            email = profile.get("email")
            if not email:
                emails_res = await client.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github+json",
                    },
                )
                emails_res.raise_for_status()
                emails = emails_res.json()
                primary = next(
                    (item for item in emails if item.get("primary") and item.get("verified")),
                    None,
                )
                fallback = next((item for item in emails if item.get("verified")), None)
                chosen = primary or fallback
                email = chosen.get("email") if chosen else None
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"GitHub OAuth request failed: {exc}") from exc

    if not email:
        raise HTTPException(status_code=400, detail="GitHub OAuth email is missing")

    user = await _get_or_create_user_from_oauth(
        db,
        email=email,
        name=profile.get("name") or profile.get("login") or email.split("@")[0],
        avatar_url=profile.get("avatar_url"),
    )
    return _build_oauth_redirect_response(
        user,
        next_path=oauth_next,
        clear_oauth_state_cookie="oauth_state_github",
        clear_oauth_next_cookie="oauth_next",
    )


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: DbSessionDep,
    request: Request,
) -> None:
    # Rate limit password reset requests (3 per 5 minutes)
    check_rate_limit(request, max_requests=3, window_seconds=300, key_suffix="forgot")
    
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user:
        return

    token = create_password_reset_token(user.email)
    reset_link = f"{settings.frontend_url}/auth/reset-password?token={token}"
    send_password_reset_email(user.email, reset_link)
    audit_password_reset_request(request, user.email, exists=True)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(payload: ResetPasswordRequest, db: DbSessionDep) -> None:
    email = decode_password_reset_token(payload.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset request",
        )

    user.hashed_password = get_password_hash(payload.new_password)
    await db.commit()
