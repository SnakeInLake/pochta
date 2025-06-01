import random
import string
import smtplib
from email.mime.text import MIMEText
import os
from .config import settings # Используем настройки из config

def generate_2fa_code(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))

def send_2fa_code_email(recipient_email: str, code: str):
    smtp_server = settings.SMTP_SERVER
    port = settings.SMTP_PORT
    sender_email = settings.EMAIL_USER
    password = settings.EMAIL_PASSWORD

    if not sender_email or not password:
        print("Ошибка: EMAIL_USER или EMAIL_PASSWORD не установлены в .env или config.")
        raise ValueError("Email credentials not configured in application settings.")

    message = MIMEText(f"Ваш одноразовый код для входа в Сейф-Папку: {code}")
    message["Subject"] = "Код подтверждения для Сейф-Папки"
    message["From"] = sender_email
    message["To"] = recipient_email

    try:
        with smtplib.SMTP(smtp_server, port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, message.as_string())
        print(f"Код 2FA успешно отправлен на {recipient_email}")
    except Exception as e:
        print(f"Ошибка при отправке письма 2FA: {e}")
        raise # Перевыбрасываем, чтобы API обработал