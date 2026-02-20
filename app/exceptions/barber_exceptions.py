# app/exceptions/barber_exceptions.py


class BarberNotFoundError(Exception):
    """Raised when a barber is not found."""

    def __init__(self, barber_id: str):
        self.barber_id = barber_id
        super().__init__(f"Barber with id '{barber_id}' not found")


class BarberServiceNotFoundError(Exception):
    """Raised when a barber service is not found."""

    def __init__(self, service_id: str):
        self.service_id = service_id
        super().__init__(f"Barber service with id '{service_id}' not found")


class BarberScheduleNotFoundError(Exception):
    """Raised when a barber schedule slot is not found."""

    def __init__(self, schedule_id: str):
        self.schedule_id = schedule_id
        super().__init__(f"Barber schedule with id '{schedule_id}' not found")


class AppointmentNotFoundError(Exception):
    """Raised when an appointment is not found."""

    def __init__(self, appointment_id: str):
        self.appointment_id = appointment_id
        super().__init__(f"Appointment with id '{appointment_id}' not found")


class AppointmentSlotUnavailableError(Exception):
    """Raised when the requested time slot is already taken or outside schedule."""

    def __init__(self, message: str = "The requested time slot is not available"):
        super().__init__(message)


class BarberAccessDeniedError(Exception):
    """Raised when user doesn't have access to barber/appointment resources."""

    def __init__(self, message: str = "Access denied to this barbershop resource"):
        super().__init__(message)
