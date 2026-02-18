import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings


logger = logging.getLogger("wishshare.mailer")


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    subject = "WishShare: сброс пароля"
    body = (
        "Вы запросили сброс пароля в WishShare.\n\n"
        f"Перейдите по ссылке, чтобы задать новый пароль:\n{reset_link}\n\n"
        "Если это были не вы, просто проигнорируйте это письмо."
    )

    if not settings.smtp_host:
        logger.info(
            "SMTP not configured. Password reset link for %s: %s",
            to_email,
            reset_link,
        )
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message.set_content(body)

    if settings.smtp_use_tls:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    else:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)


def send_email_verification_email(to_email: str, verify_link: str) -> None:
    subject = "WishShare: подтверждение email"
    body = (
        "Подтвердите email для WishShare.\n\n"
        f"Перейдите по ссылке для подтверждения:\n{verify_link}\n\n"
        "Если это были не вы, просто проигнорируйте это письмо."
    )

    if not settings.smtp_host:
        logger.info(
            "SMTP not configured. Email verification link for %s: %s",
            to_email,
            verify_link,
        )
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message.set_content(body)

    if settings.smtp_use_tls:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    else:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)


def send_unavailable_gift_notice(to_email: str, wishlist_title: str, gift_title: str) -> None:
    subject = "WishShare: товар стал недоступен"
    body = (
        f"В вашем вишлисте '{wishlist_title}' товар '{gift_title}' стал недоступен.\n\n"
        "Замените его альтернативой или обновите ссылку на товар."
    )

    if not settings.smtp_host:
        logger.info(
            "SMTP not configured. Unavailable gift notice for %s: %s — %s",
            to_email,
            wishlist_title,
            gift_title,
        )
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message.set_content(body)

    if settings.smtp_use_tls:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    else:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
