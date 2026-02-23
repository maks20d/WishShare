"""
Async-safe email sender.

smtplib is blocking; we wrap every send in asyncio.get_event_loop().run_in_executor
so that the FastAPI event loop is never blocked waiting for SMTP.
"""
import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Callable

from app.core.config import settings

logger = logging.getLogger("wishshare.mailer")


# ── low-level sync helpers ────────────────────────────────────────────────────

def _build_message(subject: str, body: str, to_email: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email
    msg.set_content(body)
    return msg


def _send_sync(msg: EmailMessage) -> None:
    """Blocking SMTP send – must be run in an executor."""
    if settings.smtp_use_tls:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)


async def _send_async(msg: EmailMessage) -> None:
    """Run blocking SMTP send in a thread pool without blocking the event loop."""
    if not settings.smtp_host:
        logger.info("SMTP not configured – skipping send to %s (subject: %s)", msg["To"], msg["Subject"])
        return
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, _send_sync, msg)
        logger.info("Email sent to %s subject=%r", msg["To"], msg["Subject"])
    except Exception:
        logger.exception("Failed to send email to %s subject=%r", msg["To"], msg["Subject"])


# ── public API ────────────────────────────────────────────────────────────────

def send_password_reset_email(to_email: str, reset_link: str) -> None:
    """
    Fire-and-forget password reset email.
    Schedules the blocking SMTP call on the event loop's thread-pool.
    """
    if not settings.smtp_host:
        logger.info("SMTP not configured. Password reset link for %s: %s", to_email, reset_link)
        return
    body = (
        "Вы запросили сброс пароля в WishShare.\n\n"
        f"Перейдите по ссылке, чтобы задать новый пароль:\n{reset_link}\n\n"
        "Если это были не вы, просто проигнорируйте это письмо."
    )
    msg = _build_message("WishShare: сброс пароля", body, to_email)
    asyncio.ensure_future(_send_async(msg))


def send_email_verification_email(to_email: str, verify_link: str) -> None:
    if not settings.smtp_host:
        logger.info("SMTP not configured. Verification link for %s: %s", to_email, verify_link)
        return
    body = (
        "Добро пожаловать в WishShare!\n\n"
        f"Подтвердите email, перейдя по ссылке:\n{verify_link}\n\n"
        "Если вы не регистрировались, проигнорируйте это письмо."
    )
    msg = _build_message("WishShare: подтверждение email", body, to_email)
    asyncio.ensure_future(_send_async(msg))


def send_unavailable_gift_notice(to_email: str, gift_title: str, wishlist_title: str) -> None:
    if not settings.smtp_host:
        return
    body = (
        f"Подарок «{gift_title}» из вишлиста «{wishlist_title}» был помечен как недоступный.\n\n"
        "Возможно, товар снят с продажи или изменилась цена. Откройте вишлист и обновите информацию."
    )
    msg = _build_message("WishShare: подарок недоступен", body, to_email)
    asyncio.ensure_future(_send_async(msg))
