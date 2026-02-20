# shared/services/notification_service.py
import smtplib
import socks
import ssl
from email.mime.text import MIMEText
from email.utils import formataddr


class NotificationService:
    """Service for sending notifications via email. Shared between app and bot-worker."""

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

        sock = socks.socksocket()
        sock.settimeout(30)
        sock.connect(('smtp.gmail.com', 587))

        server = smtplib.SMTP()
        server.sock = sock
        server._host = 'smtp.gmail.com'

        code, msg_response = server.getreply()
        if code != 220:
            raise Exception(f"SMTP connection failed: {code} {msg_response}")

        server.ehlo()

        context = ssl.create_default_context()
        server.starttls(context=context)
        server.ehlo()

        server.login(NotificationService.MY_EMAIL, NotificationService.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

    @staticmethod
    async def send_booking_notification(
            owner_email: str,
            business_name: str,
            guest_name: str,
            table_number: int,
            booking_date: str,
            booking_time: str,
            num_guests: int,
            guest_phone: str = None
    ) -> None:
        """Send booking notification to restaurant owner."""
        phone_info = f"\nТелефон: {guest_phone}" if guest_phone else ""

        subject = f"Новое бронирование в {business_name}"
        body = f"""
Здравствуйте!

Новое бронирование столика:

📅 Дата: {booking_date}
🕐 Время: {booking_time}
🪑 Столик: #{table_number}
👥 Количество гостей: {num_guests}
👤 Имя гостя: {guest_name}{phone_info}

---
Это автоматическое уведомление от вашей системы бронирования.
        """.strip()

        await NotificationService.send_email(
            to=owner_email,
            subject=subject,
            body=body
        )

    @staticmethod
    async def send_barbershop_appointment_notification(
            owner_email: str,
            business_name: str,
            client_name: str,
            client_phone: str,
            barber_name: str,
            service_name: str,
            appointment_date: str,
            appointment_time: str,
            duration_minutes: int,
    ) -> None:
        """Send new appointment notification to barbershop owner."""
        subject = f"Новая запись в {business_name}"
        body = f"""
Здравствуйте!

Новая запись в барбершоп:

✂️ Мастер: {barber_name}
💈 Услуга: {service_name}
📅 Дата: {appointment_date}
🕐 Время: {appointment_time}
⏱️ Длительность: {duration_minutes} мин.
👤 Клиент: {client_name}
📞 Телефон: {client_phone}

---
Это автоматическое уведомление от вашей системы бронирования.
        """.strip()

        await NotificationService.send_email(
            to=owner_email,
            subject=subject,
            body=body
        )

    @staticmethod
    async def send_barbershop_reschedule_notification(
            owner_email: str,
            business_name: str,
            client_name: str,
            barber_name: str,
            old_date: str,
            old_time: str,
            new_date: str,
            new_time: str,
    ) -> None:
        """Send reschedule notification to barbershop owner."""
        subject = f"Перенос записи в {business_name}"
        body = f"""
Здравствуйте!

Клиент перенёс запись:

✂️ Мастер: {barber_name}
👤 Клиент: {client_name}

Было: 📅 {old_date} 🕐 {old_time}
Стало: 📅 {new_date} 🕐 {new_time}

---
Это автоматическое уведомление от вашей системы бронирования.
        """.strip()

        await NotificationService.send_email(
            to=owner_email,
            subject=subject,
            body=body
        )

    @staticmethod
    async def send_barbershop_cancellation_notification(
            owner_email: str,
            business_name: str,
            client_name: str,
            barber_name: str,
            appointment_date: str,
            appointment_time: str,
    ) -> None:
        """Send cancellation notification to barbershop owner."""
        subject = f"Отмена записи в {business_name}"
        body = f"""
Здравствуйте!

Клиент отменил запись:

✂️ Мастер: {barber_name}
👤 Клиент: {client_name}
📅 Дата: {appointment_date}
🕐 Время: {appointment_time}

---
Это автоматическое уведомление от вашей системы бронирования.
        """.strip()

        await NotificationService.send_email(
            to=owner_email,
            subject=subject,
            body=body
        )
