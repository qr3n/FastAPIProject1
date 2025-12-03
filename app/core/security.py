# app/core/security.py
import secrets
import hashlib
import random
from datetime import datetime, timedelta, timezone
from app.core.config import settings


def generate_session_id() -> str:
    """
    Generate a cryptographically secure session ID.

    Returns:
        64-character hexadecimal session ID
    """
    return secrets.token_hex(32)


def hash_session_id(session_id: str) -> str:
    """
    Hash session ID for storage in database.

    Args:
        session_id: Plain session ID

    Returns:
        SHA-256 hash of session ID
    """
    return hashlib.sha256(session_id.encode()).hexdigest()


def generate_verification_code() -> str:
    """
    Generate a 6-digit verification code.

    Returns:
        6-digit code as string
    """
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])


def hash_verification_code(code: str) -> str:
    """
    Hash verification code for storage.

    Args:
        code: Plain verification code

    Returns:
        SHA-256 hash of code
    """
    return hashlib.sha256(code.encode()).hexdigest()


def get_session_expiry() -> datetime:
    """
    Calculate session expiry datetime.

    Returns:
        Datetime when session should expire (timezone-aware UTC)
    """
    return datetime.now(timezone.utc) + timedelta(seconds=settings.SESSION_MAX_AGE)


def get_verification_code_expiry() -> datetime:
    """
    Calculate verification code expiry datetime.

    Returns:
        Datetime when code should expire (timezone-aware UTC)
    """
    return datetime.now(timezone.utc) + timedelta(
        seconds=settings.VERIFICATION_CODE_EXPIRY
    )


def get_current_utc_time() -> datetime:
    """
    Get current UTC time as timezone-aware datetime.

    Returns:
        Current UTC datetime
    """
    return datetime.now(timezone.utc)


def is_valid_email(email: str) -> bool:
    """
    Basic email validation.

    Args:
        email: Email to validate

    Returns:
        True if email format is valid
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_phone(phone: str) -> bool:
    """
    Basic phone validation (international format).

    Args:
        phone: Phone number to validate

    Returns:
        True if phone format is valid
    """
    import re
    pattern = r'^\+?[1-9]\d{1,14}$'
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    return bool(re.match(pattern, cleaned))


def normalize_phone(phone: str) -> str:
    """
    Normalize phone number to international format.

    Args:
        phone: Phone number

    Returns:
        Normalized phone number
    """
    import re
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    if not cleaned.startswith('+'):
        cleaned = '+' + cleaned
    return cleaned