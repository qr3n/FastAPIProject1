# app/services/notification_service.py
import smtplib
import socks
import ssl
from email.mime.text import MIMEText
from email.utils import formataddr

from app.core.config import settings


class NotificationService:
    """Service for sending notifications via email and SMS."""

    EMAIL_PASSWORD = 'tevy zzdx vksa vqid'
    MY_EMAIL = 'qren.freelance@gmail.com'

    # Настройки SOCKS5 прокси
    PROXY_HOST = '130.254.42.166'
    PROXY_PORT = 12325
    PROXY_USER = 'user210158'
    PROXY_PASS = '03bnt7'

    @staticmethod
    async def send_email(to: str, subject: str, body: str) -> None:
        """
        Send email using Gmail SMTP through SOCKS5 proxy.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body text
        """
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = formataddr(('Добро пожаловать!', NotificationService.MY_EMAIL))
        msg['To'] = to

        # Создаём сокет через SOCKS5 прокси
        sock = socks.socksocket()
        sock.set_proxy(
            proxy_type=socks.SOCKS5,
            addr=NotificationService.PROXY_HOST,
            port=NotificationService.PROXY_PORT,
            username=NotificationService.PROXY_USER,
            password=NotificationService.PROXY_PASS
        )
        sock.settimeout(30)
        sock.connect(('smtp.gmail.com', 587))

        # Создаём SMTP с подключенным сокетом
        server = smtplib.SMTP()
        server.sock = sock

        # Устанавливаем hostname для TLS
        server._host = 'smtp.gmail.com'

        # Получаем приветствие от SMTP сервера
        code, msg_response = server.getreply()
        if code != 220:
            raise Exception(f"SMTP connection failed: {code} {msg_response}")

        # SMTP процесс с явным указанием hostname для TLS
        server.ehlo()

        # Создаём SSL контекст и оборачиваем сокет
        context = ssl.create_default_context()
        server.starttls(context=context)
        server.ehlo()

        server.login(NotificationService.MY_EMAIL, NotificationService.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

    @staticmethod
    async def send_sms(phone: str, body: str) -> None:
        """
        Send SMS using SMSC.ru API.

        Args:
            phone: Recipient phone number
            body: SMS text
        """
        from app.lib.smsc_api import smsc
        smsc.send_sms(phone, body)

    @staticmethod
    async def send_verification_code(
            contact: str,
            contact_type: str,
            code: str
    ) -> None:
        """
        Send verification code via email or SMS.

        Args:
            contact: Email or phone number
            contact_type: Type of contact ('email' or 'phone')
            code: Verification code to send
        """
        message = f"Ваш код подтверждения: {code}\n\nКод действителен 10 минут."

        if contact_type == 'email':
            await NotificationService.send_email(
                to=contact,
                subject='Код подтверждения',
                body=message
            )
        elif contact_type == 'phone':
            await NotificationService.send_sms(
                phone=contact,
                body=f"Ваш код: {code}"
            )