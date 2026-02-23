import logging
import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import settings


logger = logging.getLogger("wishshare.mailer")


def _get_base_html_template(title: str, content: str, button_text: Optional[str] = None, button_link: Optional[str] = None) -> str:
    """Базовый HTML-шаблон для писем WishShare."""
    button_html = ""
    if button_text and button_link:
        button_html = f'''
        <div style="text-align: center; margin: 30px 0;">
            <a href="{button_link}" style="display: inline-block; padding: 14px 28px; background-color: #6366f1; color: #ffffff; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px;">
                {button_text}
            </a>
        </div>'''
    
    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <tr>
            <td style="background-color: #ffffff; border-radius: 16px; padding: 40px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                <!-- Header -->
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="margin: 0; font-size: 28px; color: #6366f1; font-weight: 700;">
                        🎁 WishShare
                    </h1>
                </div>
                
                <!-- Title -->
                <h2 style="margin: 0 0 20px 0; font-size: 22px; color: #1f2937; text-align: center;">
                    {title}
                </h2>
                
                <!-- Content -->
                <div style="color: #4b5563; font-size: 16px; line-height: 1.6;">
                    {content}
                </div>
                
                {button_html}
                
                <!-- Footer -->
                <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb; text-align: center;">
                    <p style="margin: 0; color: #9ca3af; font-size: 14px;">
                        Это автоматическое уведомление от WishShare
                    </p>
                    <p style="margin: 10px 0 0 0; color: #9ca3af; font-size: 12px;">
                        Если вы не хотите получать эти уведомления, вы можете отключить их в настройках профиля
                    </p>
                </div>
            </td>
        </tr>
    </table>
</body>
</html>'''


def _send_email(to_email: str, subject: str, text_body: str, html_body: str) -> None:
    """Отправка email с HTML и текстовой версией."""
    if not settings.smtp_host:
        logger.info(
            "SMTP not configured. Email for %s would be sent: %s",
            to_email,
            subject,
        )
        return
    
    if not settings.email_notifications_enabled:
        logger.info(
            "Email notifications disabled. Skipping email to %s: %s",
            to_email,
            subject,
        )
        return

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    
    message.attach(MIMEText(text_body, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
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
        logger.info("Email sent successfully to %s: %s", to_email, subject)
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, str(e))


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


def send_gift_reserved_email(
    to_email: str,
    gift_title: str,
    wishlist_title: str,
    wishlist_link: str,
    reserved_by_name: Optional[str] = None,
    is_secret_santa: bool = False,
) -> None:
    """
    Отправка уведомления о бронировании подарка.
    
    Args:
        to_email: Email владельца вишлиста
        gift_title: Название забронированного подарка
        wishlist_title: Название вишлиста
        wishlist_link: Ссылка на вишлист
        reserved_by_name: Имя пользователя, забронировавшего подарок (None если Secret Santa)
        is_secret_santa: Является ли бронирование Secret Santa
    """
    subject = "🎁 Ваш подарок забронирован"
    
    if is_secret_santa or not reserved_by_name:
        reserved_info = "участник Secret Santa"
        reserved_text = "Кто-то забронировал ваш подарок в режиме Secret Santa 🎅"
    else:
        reserved_info = reserved_by_name
        reserved_text = f"<strong>{reserved_by_name}</strong> забронировал(а) ваш подарок"
    
    text_body = (
        f"Ваш подарок забронирован!\n\n"
        f"Подарок: {gift_title}\n"
        f"Вишлист: {wishlist_title}\n"
        f"Забронировал: {reserved_info}\n\n"
        f"Перейдите в вишлист: {wishlist_link}"
    )
    
    html_content = f'''
    <div style="text-align: center; margin-bottom: 20px;">
        <span style="font-size: 48px;">🎉</span>
    </div>
    <p style="text-align: center; font-size: 18px; color: #1f2937; margin-bottom: 24px;">
        {reserved_text}
    </p>
    <div style="background-color: #f9fafb; border-radius: 12px; padding: 20px; margin: 20px 0;">
        <p style="margin: 0 0 12px 0; color: #6b7280; font-size: 14px;">Подарок:</p>
        <p style="margin: 0 0 16px 0; font-size: 18px; font-weight: 600; color: #1f2937;">{gift_title}</p>
        <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 14px;">Вишлист:</p>
        <p style="margin: 0; font-size: 16px; color: #4b5563;">{wishlist_title}</p>
    </div>
    '''
    
    html_body = _get_base_html_template(
        title="Подарок забронирован",
        content=html_content,
        button_text="Открыть вишлист",
        button_link=wishlist_link,
    )
    
    _send_email(to_email, subject, text_body, html_body)


def send_gift_unreserved_email(
    to_email: str,
    gift_title: str,
    wishlist_title: str,
    wishlist_link: str,
) -> None:
    """
    Отправка уведомления о снятии брони с подарка.
    
    Args:
        to_email: Email владельца вишлиста
        gift_title: Название подарка
        wishlist_title: Название вишлиста
        wishlist_link: Ссылка на вишлист
    """
    subject = "🔓 Бронь подарка снята"
    
    text_body = (
        f"Бронь с вашего подарка снята.\n\n"
        f"Подарок: {gift_title}\n"
        f"Вишлист: {wishlist_title}\n\n"
        f"Перейдите в вишлист: {wishlist_link}"
    )
    
    html_content = f'''
    <div style="text-align: center; margin-bottom: 20px;">
        <span style="font-size: 48px;">🔓</span>
    </div>
    <p style="text-align: center; font-size: 18px; color: #1f2937; margin-bottom: 24px;">
        Бронь с вашего подарка была снята. Теперь он снова доступен для бронирования.
    </p>
    <div style="background-color: #f9fafb; border-radius: 12px; padding: 20px; margin: 20px 0;">
        <p style="margin: 0 0 12px 0; color: #6b7280; font-size: 14px;">Подарок:</p>
        <p style="margin: 0 0 16px 0; font-size: 18px; font-weight: 600; color: #1f2937;">{gift_title}</p>
        <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 14px;">Вишлист:</p>
        <p style="margin: 0; font-size: 16px; color: #4b5563;">{wishlist_title}</p>
    </div>
    '''
    
    html_body = _get_base_html_template(
        title="Бронь снята",
        content=html_content,
        button_text="Открыть вишлист",
        button_link=wishlist_link,
    )
    
    _send_email(to_email, subject, text_body, html_body)


def send_contribution_email(
    to_email: str,
    gift_title: str,
    wishlist_title: str,
    wishlist_link: str,
    contribution_amount: float,
    total_collected: float,
    target_amount: float,
    contributor_name: Optional[str] = None,
    is_secret: bool = False,
) -> None:
    """
    Отправка уведомления о новом взносе в коллективный подарок.
    
    Args:
        to_email: Email владельца вишлиста
        gift_title: Название коллективного подарка
        wishlist_title: Название вишлиста
        wishlist_link: Ссылка на вишлист
        contribution_amount: Сумма взноса
        total_collected: Общая собранная сумма
        target_amount: Целевая сумма
        contributor_name: Имя внесшего (None если анонимный взнос)
        is_secret: Является ли взнос секретным
    """
    subject = "💰 Новый взнос на ваш подарок"
    
    progress_percent = min(100, int((total_collected / target_amount) * 100)) if target_amount > 0 else 0
    
    if is_secret or not contributor_name:
        contributor_info = "Анонимный участник"
    else:
        contributor_info = contributor_name
    
    text_body = (
        f"Новый взнос на ваш коллективный подарок!\n\n"
        f"Подарок: {gift_title}\n"
        f"Взнос: {contribution_amount:.2f} ₽\n"
        f"Внёс: {contributor_info}\n\n"
        f"Прогресс: {total_collected:.2f} / {target_amount:.2f} ₽ ({progress_percent}%)\n\n"
        f"Перейдите в вишлист: {wishlist_link}"
    )
    
    html_content = f'''
    <div style="text-align: center; margin-bottom: 20px;">
        <span style="font-size: 48px;">💰</span>
    </div>
    <p style="text-align: center; font-size: 18px; color: #1f2937; margin-bottom: 24px;">
        Новый взнос на ваш коллективный подарок!
    </p>
    <div style="background-color: #f9fafb; border-radius: 12px; padding: 20px; margin: 20px 0;">
        <p style="margin: 0 0 12px 0; color: #6b7280; font-size: 14px;">Подарок:</p>
        <p style="margin: 0 0 16px 0; font-size: 18px; font-weight: 600; color: #1f2937;">{gift_title}</p>
        <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 14px;">Внёс:</p>
        <p style="margin: 0 0 16px 0; font-size: 16px; color: #4b5563;">{contributor_info}</p>
        <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 14px;">Сумма взноса:</p>
        <p style="margin: 0; font-size: 24px; font-weight: 700; color: #10b981;">{contribution_amount:.2f} ₽</p>
    </div>
    <div style="margin: 24px 0;">
        <p style="margin: 0 0 12px 0; color: #6b7280; font-size: 14px; text-align: center;">
            Прогресс сбора: {total_collected:.2f} / {target_amount:.2f} ₽
        </p>
        <div style="background-color: #e5e7eb; border-radius: 8px; height: 12px; overflow: hidden;">
            <div style="background: linear-gradient(90deg, #6366f1, #8b5cf6); height: 100%; width: {progress_percent}%; border-radius: 8px;"></div>
        </div>
        <p style="margin: 8px 0 0 0; color: #6366f1; font-size: 14px; font-weight: 600; text-align: center;">
            {progress_percent}% собрано
        </p>
    </div>
    '''
    
    html_body = _get_base_html_template(
        title="Новый взнос",
        content=html_content,
        button_text="Открыть вишлист",
        button_link=wishlist_link,
    )
    
    _send_email(to_email, subject, text_body, html_body)
