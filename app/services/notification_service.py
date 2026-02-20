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
        """
        Send booking notification to business owner.

        Args:
            owner_email: Business owner's email
            business_name: Name of the business
            guest_name: Name of the guest
            table_number: Table number
            booking_date: Date of booking
            booking_time: Time of booking
            num_guests: Number of guests
            guest_phone: Guest phone number (optional)
        """
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
        # sock.set_proxy(
        #     proxy_type=socks.SOCKS5,
        #     addr=NotificationService.PROXY_HOST,
        #     port=NotificationService.PROXY_PORT,
        #     username=NotificationService.PROXY_USER,
        #     password=NotificationService.PROXY_PASS
        # )
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
        """
        Send new appointment notification to barbershop owner.

        Args:
            owner_email: Business owner's email
            business_name: Name of the barbershop
            client_name: Name of the client
            client_phone: Client's phone number
            barber_name: Name of the barber
            service_name: Name of the service
            appointment_date: Date of appointment
            appointment_time: Time of appointment
            duration_minutes: Duration of service in minutes
        """
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
        """
        Send reschedule notification to barbershop owner.

        Args:
            owner_email: Business owner's email
            business_name: Name of the barbershop
            client_name: Name of the client
            barber_name: Name of the barber
            old_date: Previous appointment date
            old_time: Previous appointment time
            new_date: New appointment date
            new_time: New appointment time
        """
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
        """
        Send cancellation notification to barbershop owner.

        Args:
            owner_email: Business owner's email
            business_name: Name of the barbershop
            client_name: Name of the client
            barber_name: Name of the barber
            appointment_date: Date of cancelled appointment
            appointment_time: Time of cancelled appointment
        """
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