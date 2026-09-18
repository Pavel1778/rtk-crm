"""
Сервис отправки email-уведомлений через SMTP (152-ФЗ compliant).
Использует российский SMTP-провайдер (Яндекс.Почта) для соблюдения 152-ФЗ.
"""
import asyncio
from typing import Optional
from loguru import logger
from aiosmtplib import SMTP, SMTPException
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings
from app.models.interaction import Interaction
from app.models.workflow_stage import WorkflowStage


def mask_email(email: str) -> str:
    """Маскирование email для логирования (152-ФЗ)."""
    if not email or "@" not in email:
        return "***"
    parts = email.split("@")
    if len(parts[0]) < 2:
        masked_local = "*"
    else:
        masked_local = parts[0][0] + "***"
    return f"{masked_local}@{parts[1]}"


async def send_email(
    to: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> bool:
    """
    Асинхронная отправка email через SMTP.
    
    Args:
        to: Email получателя
        subject: Тема письма
        html_body: HTML-тело письма
        text_body: Plain-text тело (опционально)
    
    Returns:
        True если успешно, False иначе
    """
    if not settings.EMAIL_ENABLED:
        logger.info(f"Email отключён. Письмо для {mask_email(to)} не отправлено.")
        return False
    
    if not settings.EMAIL_USER or not settings.EMAIL_PASSWORD:
        logger.error("SMTP credentials не настроены. Отмена отправки.")
        return False
    
    # Создаём сообщение
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    msg["To"] = to
    
    # Добавляем текстовую и HTML версии
    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    
    # Параметры подключения
    smtp_hostname = settings.EMAIL_HOST
    smtp_port = settings.EMAIL_PORT
    use_tls = settings.EMAIL_USE_TLS
    username = settings.EMAIL_USER
    password = settings.EMAIL_PASSWORD
    
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # Создаём SMTP клиент
            smtp = SMTP(hostname=smtp_hostname, port=smtp_port, use_tls=use_tls)
            
            # Подключаемся и авторизуемся
            await smtp.connect()
            await smtp.login(username, password)
            
            # Отправляем письмо
            await smtp.send_message(msg)
            
            logger.info(f"Email успешно отправлен: {mask_email(to)}")
            return True
            
        except SMTPException as e:
            logger.warning(
                f"SMTP ошибка при отправке {mask_email(to)} (попытка {attempt + 1}/{max_retries}): {e}"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (2 ** attempt))  # Экспоненциальная задержка
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке email {mask_email(to)}: {e}")
            return False
    
    logger.error(f"Не удалось отправить email после {max_retries} попыток: {mask_email(to)}")
    return False


async def send_status_change_notification(
    interaction: Interaction,
    new_stage: WorkflowStage,
    recipient_email: str,
) -> bool:
    """
    Отправка уведомления о смене статуса взаимодействия.
    
    Args:
        interaction: Объект взаимодействия
        new_stage: Новый этап workflow
        recipient_email: Email получателя (КАМ)
    
    Returns:
        True если успешно, False иначе
    """
    from app.services.email_templates import status_change_email_html
    
    # Получаем название ВУЗа
    university_name = interaction.university.name if interaction.university else "ВУЗ"
    
    # Получаем предыдущий этап из истории (если есть)
    old_stage_title = "Неизвестно"
    if interaction.history and len(interaction.history) > 0:
        # Берем последний запись из истории
        last_history = sorted(interaction.history, key=lambda x: x.created_at, reverse=True)[0]
        old_stage_title = last_history.old_stage_title if hasattr(last_history, 'old_stage_title') else "Предыдущий этап"
    else:
        old_stage_title = "Начальный этап"
    
    contract_number = interaction.contract_number or "Б/н"
    
    # Генерируем HTML
    html_body = status_change_email_html(
        university_name=university_name,
        old_stage=old_stage_title,
        new_stage=new_stage.title,
        contract_number=contract_number,
    )
    
    subject = f"RTK CRM: Статус изменён — {university_name}"
    
    # Отправляем
    success = await send_email(
        to=recipient_email,
        subject=subject,
        html_body=html_body,
    )
    
    return success
