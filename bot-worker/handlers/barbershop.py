# bot-worker/handlers/barbershop.py
"""
Barbershop Telegram bot handlers.

Flow:
  /start  → welcome + main menu
  /book   → choose master → choose service → choose date → choose time → confirm
  /my     → list user's upcoming appointments → reschedule / cancel
  /masters → list all barbers with their services
"""
import logging
from datetime import date, timedelta
from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from shared.models.barber import (
    Barber,
    BarberService,
    BarberSchedule,
    BarberAppointment,
    AppointmentStatus,
)
from shared.models.tg_user import TGUser
from shared.models.business import Business
from shared.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

DAYS_AHEAD = 14  # how many days to offer for booking


# ─────────────────────────── FSM States ───────────────────────────

class BookingState(StatesGroup):
    choosing_barber = State()
    choosing_service = State()
    entering_date = State()
    choosing_time = State()
    entering_name = State()
    entering_phone = State()
    confirming = State()


class RescheduleState(StatesGroup):
    choosing_appointment = State()
    entering_date = State()
    choosing_time = State()
    confirming = State()


# ─────────────────────────── Helpers ───────────────────────────

def _barbers_keyboard(barbers: list[Barber]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"✂️ {b.name}" + (f" — {b.specialization}" if b.specialization else ""),
            callback_data=f"bs_barber:{b.id}"
        )]
        for b in barbers
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _services_keyboard(services: list[BarberService]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"{s.name} — {s.price}₽ ({s.duration_minutes} мин)",
            callback_data=f"bs_service:{s.id}"
        )]
        for s in services
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="bs_back_barber")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _dates_keyboard() -> InlineKeyboardMarkup:
    today = date.today()
    buttons = []
    for i in range(DAYS_AHEAD):
        d = today + timedelta(days=i)
        label = d.strftime("%d.%m (%a)")
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"bs_date:{d.isoformat()}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="bs_back_service")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _times_keyboard(slots: list[str]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=slot, callback_data=f"bs_time:{slot}")]
        for slot in slots
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="bs_back_date")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _appointments_keyboard(appts: list[BarberAppointment]) -> InlineKeyboardMarkup:
    buttons = []
    for a in appts:
        label = f"{a.appointment_date} {str(a.appointment_time)[:5]} — {a.barber.name}"
        buttons.append([
            InlineKeyboardButton(
                text=f"🔄 Перенести: {label}",
                callback_data=f"bs_reschedule:{a.id}"
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text=f"❌ Отменить: {label}",
                callback_data=f"bs_cancel:{a.id}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def _get_owner_email(business_id: str) -> str | None:
    """Fetch business owner email for notifications."""
    try:
        business = await Business.get_or_none(id=business_id).prefetch_related("owner")
        if business and business.owner and business.owner.email:
            return business.owner.email
    except Exception as e:
        logger.warning(f"Could not fetch owner email: {e}")
    return None


async def _get_or_create_user(from_user) -> TGUser:
    from datetime import datetime
    user = await TGUser.filter(telegram_id=from_user.id).first()
    if not user:
        user = await TGUser.create(
            telegram_id=from_user.id,
            username=from_user.username,
            first_name=from_user.first_name,
            last_name=from_user.last_name,
            language_code=getattr(from_user, "language_code", "ru") or "ru",
            last_interaction=datetime.utcnow(),
        )
    else:
        from datetime import datetime
        user.last_interaction = datetime.utcnow()
        await user.save()
    return user


async def _get_available_slots(barber_id: str, target_date: str) -> list[str]:
    appt_date = date.fromisoformat(target_date)
    weekday = appt_date.weekday()

    schedules = await BarberSchedule.filter(
        barber_id=barber_id,
        weekday=weekday,
        is_active=True,
    ).all()

    if not schedules:
        return []

    booked = await BarberAppointment.filter(
        barber_id=barber_id,
        appointment_date=appt_date,
        status__not_in=[AppointmentStatus.CANCELLED],
    ).values_list("appointment_time", flat=True)

    booked_times = {str(t)[:5] for t in booked}
    available = [str(s.start_time)[:5] for s in schedules if str(s.start_time)[:5] not in booked_times]
    return sorted(available)


# ─────────────────────────── Register handlers ───────────────────────────

def register_barbershop_handlers(router: Router, business_id: str):
    """Register all barbershop handlers on the given router."""

    # ── /start ────────────────────────────────────────────────────────

    @router.message(Command("start"))
    async def cmd_start(message: Message, state: FSMContext):
        await state.clear()
        await _get_or_create_user(message.from_user)
        business = await Business.get_or_none(id=business_id)
        name = business.name if business else "Барбершоп"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✂️ Записаться", callback_data="bs_start_book")],
            [InlineKeyboardButton(text="📋 Мои записи", callback_data="bs_my_appointments")],
            [InlineKeyboardButton(text="👨‍🦱 Наши мастера", callback_data="bs_masters")],
        ])
        await message.answer(
            f"👋 Добро пожаловать в <b>{name}</b>!\n\n"
            "Выберите действие:",
            reply_markup=keyboard,
        )

    # ── /book ─────────────────────────────────────────────────────────

    @router.message(Command("book"))
    @router.callback_query(F.data == "bs_start_book")
    async def cmd_book(update: Message | CallbackQuery, state: FSMContext):
        await state.clear()
        msg = update.message if isinstance(update, CallbackQuery) else update

        barbers = await Barber.filter(business_id=business_id, is_active=True).all()
        if not barbers:
            await msg.answer("😔 В данный момент нет доступных мастеров.")
            if isinstance(update, CallbackQuery):
                await update.answer()
            return

        await state.set_state(BookingState.choosing_barber)
        await msg.answer("✂️ <b>Выберите мастера:</b>", reply_markup=_barbers_keyboard(barbers))
        if isinstance(update, CallbackQuery):
            await update.answer()

    # ── Choose barber ─────────────────────────────────────────────────

    @router.callback_query(F.data.startswith("bs_barber:"), BookingState.choosing_barber)
    async def cb_choose_barber(callback: CallbackQuery, state: FSMContext):
        barber_id_chosen = callback.data.split(":")[1]
        barber = await Barber.get_or_none(id=barber_id_chosen)
        if not barber:
            await callback.answer("Мастер не найден", show_alert=True)
            return

        await state.update_data(barber_id=barber_id_chosen, barber_name=barber.name)

        services = await BarberService.filter(barber_id=barber_id_chosen, is_active=True).all()
        if not services:
            await callback.message.answer("😔 У этого мастера пока нет доступных услуг.")
            await callback.answer()
            return

        await state.set_state(BookingState.choosing_service)
        await callback.message.edit_text(
            f"✂️ Мастер: <b>{barber.name}</b>\n\nВыберите услугу:",
            reply_markup=_services_keyboard(services),
        )
        await callback.answer()

    @router.callback_query(F.data == "bs_back_barber")
    async def cb_back_to_barber(callback: CallbackQuery, state: FSMContext):
        barbers = await Barber.filter(business_id=business_id, is_active=True).all()
        await state.set_state(BookingState.choosing_barber)
        await callback.message.edit_text(
            "✂️ <b>Выберите мастера:</b>",
            reply_markup=_barbers_keyboard(barbers),
        )
        await callback.answer()

    # ── Choose service ────────────────────────────────────────────────

    @router.callback_query(F.data.startswith("bs_service:"), BookingState.choosing_service)
    async def cb_choose_service(callback: CallbackQuery, state: FSMContext):
        service_id_chosen = callback.data.split(":")[1]
        svc = await BarberService.get_or_none(id=service_id_chosen)
        if not svc:
            await callback.answer("Услуга не найдена", show_alert=True)
            return

        await state.update_data(service_id=service_id_chosen, service_name=svc.name)
        await state.set_state(BookingState.entering_date)

        await callback.message.edit_text(
            f"📅 Услуга: <b>{svc.name}</b>\n\nВыберите дату:",
            reply_markup=_dates_keyboard(),
        )
        await callback.answer()

    @router.callback_query(F.data == "bs_back_service")
    async def cb_back_to_service(callback: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        services = await BarberService.filter(barber_id=data.get("barber_id"), is_active=True).all()
        await state.set_state(BookingState.choosing_service)
        await callback.message.edit_text(
            f"Выберите услугу:",
            reply_markup=_services_keyboard(services),
        )
        await callback.answer()

    # ── Choose date ───────────────────────────────────────────────────

    @router.callback_query(F.data.startswith("bs_date:"), BookingState.entering_date)
    async def cb_choose_date(callback: CallbackQuery, state: FSMContext):
        chosen_date = callback.data.split(":")[1]
        data = await state.get_data()
        slots = await _get_available_slots(data["barber_id"], chosen_date)

        if not slots:
            await callback.answer("На эту дату нет свободного времени. Выберите другую.", show_alert=True)
            return

        await state.update_data(appointment_date=chosen_date)
        await state.set_state(BookingState.choosing_time)
        await callback.message.edit_text(
            f"🕐 Выберите время на <b>{chosen_date}</b>:",
            reply_markup=_times_keyboard(slots),
        )
        await callback.answer()

    @router.callback_query(F.data == "bs_back_date")
    async def cb_back_to_date(callback: CallbackQuery, state: FSMContext):
        await state.set_state(BookingState.entering_date)
        await callback.message.edit_text(
            "📅 Выберите дату:",
            reply_markup=_dates_keyboard(),
        )
        await callback.answer()

    # ── Choose time ───────────────────────────────────────────────────

    @router.callback_query(F.data.startswith("bs_time:"), BookingState.choosing_time)
    async def cb_choose_time(callback: CallbackQuery, state: FSMContext):
        chosen_time = callback.data.split(":")[1]
        await state.update_data(appointment_time=chosen_time)
        await state.set_state(BookingState.entering_name)
        await callback.message.edit_text(
            f"✅ Время выбрано: <b>{chosen_time}</b>\n\n"
            "Введите ваше имя:"
        )
        await callback.answer()

    # ── Enter name ────────────────────────────────────────────────────

    @router.message(BookingState.entering_name, F.text)
    async def msg_enter_name(message: Message, state: FSMContext):
        await state.update_data(guest_name=message.text.strip())
        await state.set_state(BookingState.entering_phone)
        await message.answer(
            "📱 Введите ваш номер телефона (или нажмите /skip чтобы пропустить):"
        )

    @router.message(BookingState.entering_phone, Command("skip"))
    async def msg_skip_phone(message: Message, state: FSMContext):
        await state.update_data(guest_phone=None)
        await _show_confirmation(message, state)

    @router.message(BookingState.entering_phone, F.text)
    async def msg_enter_phone(message: Message, state: FSMContext):
        await state.update_data(guest_phone=message.text.strip())
        await _show_confirmation(message, state)

    async def _show_confirmation(message: Message, state: FSMContext):
        data = await state.get_data()
        await state.set_state(BookingState.confirming)
        text = (
            "📋 <b>Подтвердите запись:</b>\n\n"
            f"✂️ Мастер: <b>{data['barber_name']}</b>\n"
            f"💇 Услуга: <b>{data['service_name']}</b>\n"
            f"📅 Дата: <b>{data['appointment_date']}</b>\n"
            f"🕐 Время: <b>{data['appointment_time']}</b>\n"
            f"👤 Имя: <b>{data['guest_name']}</b>\n"
        )
        if data.get("guest_phone"):
            text += f"📱 Телефон: <b>{data['guest_phone']}</b>\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="bs_confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="bs_cancel_booking"),
            ]
        ])
        await message.answer(text, reply_markup=keyboard)

    # ── Confirm booking ───────────────────────────────────────────────

    @router.callback_query(F.data == "bs_confirm", BookingState.confirming)
    async def cb_confirm_booking(callback: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        user = await _get_or_create_user(callback.from_user)

        # Re-check slot availability
        slots = await _get_available_slots(data["barber_id"], data["appointment_date"])
        if data["appointment_time"] not in slots:
            await callback.answer("😔 Это время уже занято. Пожалуйста, выберите другое.", show_alert=True)
            await state.clear()
            return

        barber = await Barber.get_or_none(id=data["barber_id"])
        svc = await BarberService.get_or_none(id=data["service_id"])
        appt_date = date.fromisoformat(data["appointment_date"])
        h, m = map(int, data["appointment_time"].split(":"))
        from datetime import time as dtime
        appt_time = dtime(h, m)

        await BarberAppointment.create(
            barber=barber,
            service=svc,
            tg_user=user,
            guest_name=data["guest_name"],
            guest_phone=data.get("guest_phone"),
            appointment_date=appt_date,
            appointment_time=appt_time,
            status=AppointmentStatus.CONFIRMED,
        )

        await state.clear()
        await callback.message.edit_text(
            "🎉 <b>Запись подтверждена!</b>\n\n"
            f"✂️ Мастер: <b>{data['barber_name']}</b>\n"
            f"📅 {data['appointment_date']} в {data['appointment_time']}\n\n"
            "Ждём вас! Чтобы посмотреть или изменить запись — /my"
        )
        await callback.answer()

        # Уведомление владельцу барбершопа
        owner_email = await _get_owner_email(business_id)
        if owner_email:
            business = await Business.get_or_none(id=business_id)
            try:
                await NotificationService.send_barbershop_appointment_notification(
                    owner_email=owner_email,
                    business_name=business.name if business else "Барбершоп",
                    client_name=data["guest_name"],
                    client_phone=data.get("guest_phone") or "не указан",
                    barber_name=data["barber_name"],
                    service_name=data["service_name"],
                    appointment_date=data["appointment_date"],
                    appointment_time=data["appointment_time"],
                    duration_minutes=svc.duration_minutes,
                )
            except Exception as e:
                logger.error(f"Failed to send appointment notification: {e}")

    @router.callback_query(F.data == "bs_cancel_booking")
    async def cb_cancel_booking_flow(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.edit_text("❌ Запись отменена.")
        await callback.answer()

    # ── /my — My appointments ─────────────────────────────────────────

    @router.message(Command("my"))
    @router.callback_query(F.data == "bs_my_appointments")
    async def cmd_my(update: Message | CallbackQuery, state: FSMContext):
        await state.clear()
        msg = update.message if isinstance(update, CallbackQuery) else update
        user = await _get_or_create_user(
            update.from_user if isinstance(update, CallbackQuery) else update.from_user
        )

        appts = await BarberAppointment.filter(
            tg_user=user,
            status__not_in=[AppointmentStatus.CANCELLED],
            appointment_date__gte=date.today(),
        ).prefetch_related("barber", "service").order_by("appointment_date", "appointment_time")

        if not appts:
            await msg.answer("У вас нет предстоящих записей.\n\nЗаписаться: /book")
            if isinstance(update, CallbackQuery):
                await update.answer()
            return

        text = "📋 <b>Ваши записи:</b>\n\n"
        for a in appts:
            text += (
                f"📅 {a.appointment_date} {str(a.appointment_time)[:5]}\n"
                f"  ✂️ {a.barber.name} — {a.service.name}\n"
                f"  Статус: {a.status.value}\n\n"
            )

        await msg.answer(text, reply_markup=_appointments_keyboard(appts))
        if isinstance(update, CallbackQuery):
            await update.answer()

    # ── Reschedule ────────────────────────────────────────────────────

    @router.callback_query(F.data.startswith("bs_reschedule:"))
    async def cb_reschedule_start(callback: CallbackQuery, state: FSMContext):
        appt_id = callback.data.split(":")[1]
        appt = await BarberAppointment.get_or_none(id=appt_id)
        if not appt:
            await callback.answer("Запись не найдена", show_alert=True)
            return

        await state.set_state(RescheduleState.choosing_appointment)
        await state.update_data(reschedule_appt_id=appt_id, reschedule_barber_id=str(appt.barber_id))
        await state.set_state(RescheduleState.entering_date)

        await callback.message.answer(
            "📅 Выберите новую дату:",
            reply_markup=_dates_keyboard(),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("bs_date:"), RescheduleState.entering_date)
    async def cb_reschedule_date(callback: CallbackQuery, state: FSMContext):
        chosen_date = callback.data.split(":")[1]
        data = await state.get_data()
        slots = await _get_available_slots(data["reschedule_barber_id"], chosen_date)

        if not slots:
            await callback.answer("На эту дату нет свободного времени.", show_alert=True)
            return

        await state.update_data(new_date=chosen_date)
        await state.set_state(RescheduleState.choosing_time)
        await callback.message.edit_text(
            f"🕐 Выберите новое время на <b>{chosen_date}</b>:",
            reply_markup=_times_keyboard(slots),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("bs_time:"), RescheduleState.choosing_time)
    async def cb_reschedule_time(callback: CallbackQuery, state: FSMContext):
        chosen_time = callback.data.split(":")[1]
        data = await state.get_data()

        appt = await BarberAppointment.get_or_none(id=data["reschedule_appt_id"])
        if not appt:
            await callback.answer("Запись не найдена", show_alert=True)
            await state.clear()
            return

        new_date = date.fromisoformat(data["new_date"])
        h, m = map(int, chosen_time.split(":"))
        from datetime import time as dtime
        new_time = dtime(h, m)

        old_date = str(appt.appointment_date)
        old_time = str(appt.appointment_time)[:5]

        appt.appointment_date = new_date
        appt.appointment_time = new_time
        appt.status = AppointmentStatus.CONFIRMED
        await appt.save()

        await appt.fetch_related("barber")

        await state.clear()
        await callback.message.edit_text(
            f"✅ Запись перенесена!\n\n"
            f"📅 Новая дата: <b>{data['new_date']}</b>\n"
            f"🕐 Время: <b>{chosen_time}</b>"
        )
        await callback.answer()

        # Уведомление владельцу о переносе
        owner_email = await _get_owner_email(business_id)
        if owner_email:
            business = await Business.get_or_none(id=business_id)
            try:
                await NotificationService.send_barbershop_reschedule_notification(
                    owner_email=owner_email,
                    business_name=business.name if business else "Барбершоп",
                    client_name=appt.guest_name,
                    barber_name=appt.barber.name,
                    old_date=old_date,
                    old_time=old_time,
                    new_date=data["new_date"],
                    new_time=chosen_time,
                )
            except Exception as e:
                logger.error(f"Failed to send reschedule notification: {e}")

    # ── Cancel appointment ────────────────────────────────────────────

    @router.callback_query(F.data.startswith("bs_cancel:"))
    async def cb_cancel_appointment(callback: CallbackQuery, state: FSMContext):
        appt_id = callback.data.split(":")[1]
        user = await _get_or_create_user(callback.from_user)

        appt = await BarberAppointment.get_or_none(id=appt_id).prefetch_related("barber", "service")
        if not appt:
            await callback.answer("Запись не найдена", show_alert=True)
            return

        if appt.tg_user_id != user.id:
            await callback.answer("Это не ваша запись", show_alert=True)
            return

        appt_date_str = str(appt.appointment_date)
        appt_time_str = str(appt.appointment_time)[:5]
        barber_name = appt.barber.name
        guest_name = appt.guest_name

        appt.status = AppointmentStatus.CANCELLED
        await appt.save()

        await callback.message.answer(
            f"❌ Запись отменена:\n"
            f"📅 {appt.appointment_date} {appt_time_str}\n"
            f"✂️ {barber_name} — {appt.service.name}"
        )
        await callback.answer()

        # Уведомление владельцу об отмене
        owner_email = await _get_owner_email(business_id)
        if owner_email:
            business = await Business.get_or_none(id=business_id)
            try:
                await NotificationService.send_barbershop_cancellation_notification(
                    owner_email=owner_email,
                    business_name=business.name if business else "Барбершоп",
                    client_name=guest_name,
                    barber_name=barber_name,
                    appointment_date=appt_date_str,
                    appointment_time=appt_time_str,
                )
            except Exception as e:
                logger.error(f"Failed to send cancellation notification: {e}")

    # ── /masters ──────────────────────────────────────────────────────

    @router.message(Command("masters"))
    @router.callback_query(F.data == "bs_masters")
    async def cmd_masters(update: Message | CallbackQuery, state: FSMContext):
        msg = update.message if isinstance(update, CallbackQuery) else update

        barbers = await Barber.filter(business_id=business_id, is_active=True).prefetch_related("services").all()
        if not barbers:
            await msg.answer("Нет доступных мастеров.")
            if isinstance(update, CallbackQuery):
                await update.answer()
            return

        for b in barbers:
            services = [s for s in b.services if s.is_active]
            svc_lines = "\n".join(
                f"  • {s.name} — {s.price}₽ ({s.duration_minutes} мин)"
                for s in services
            ) or "  Услуги не указаны"

            spec = f"\n🎯 {b.specialization}" if b.specialization else ""
            desc = f"\n{b.description}" if b.description else ""
            text = f"✂️ <b>{b.name}</b>{spec}{desc}\n\n<b>Услуги:</b>\n{svc_lines}"

            await msg.answer(text)

        if isinstance(update, CallbackQuery):
            await update.answer()
