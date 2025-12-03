# app/services/auth_service.py
from datetime import timedelta
from typing import Optional
from fastapi import Request

from shared.models.user import User, Session, VerificationCode
from app.schemas.user import SendCodeSchema, VerifyCodeSchema
from app.core.security import (
    generate_session_id,
    hash_session_id,
    get_session_expiry,
    get_current_utc_time,
    generate_verification_code,
    hash_verification_code,
    get_verification_code_expiry
)
from app.services.notification_service import NotificationService
from app.exceptions.auth_exceptions import (
    InvalidSessionError,
    SessionExpiredError,
    UserNotActiveError,
    InvalidVerificationCodeError,
    VerificationCodeExpiredError,
    TooManyAttemptsError,
    CodeAlreadyUsedError,
    RateLimitError
)


class AuthService:
    """Service for passwordless authentication and session management."""

    MAX_ATTEMPTS = 3
    RATE_LIMIT_MINUTES = 1

    @staticmethod
    async def send_verification_code(data: SendCodeSchema) -> dict:
        """
        Send verification code to email or phone.

        Args:
            data: Send code request data

        Returns:
            Dict with success status

        Raises:
            RateLimitError: If too many requests in short time
        """
        contact = data.contact
        contact_type = 'email' if '@' in contact else 'phone'

        recent_code = await VerificationCode.filter(
            contact=contact,
            created_at__gte=get_current_utc_time() - timedelta(
                minutes=AuthService.RATE_LIMIT_MINUTES
            )
        ).first()

        if recent_code:
            raise RateLimitError(
                f"Please wait {AuthService.RATE_LIMIT_MINUTES} minute(s) before requesting a new code"
            )

        code = generate_verification_code()
        code_hash = hash_verification_code(code)

        await VerificationCode.create(
            contact=contact,
            contact_type=contact_type,
            code_hash=code_hash,
            expires_at=get_verification_code_expiry()
        )

        await NotificationService.send_verification_code(
            contact=contact,
            contact_type=contact_type,
            code=code
        )

        return {
            "success": True,
            "message": f"Verification code sent to {contact}"
        }

    @staticmethod
    async def verify_code_and_login(
        data: VerifyCodeSchema,
        request: Request
    ) -> tuple[str, Session, User]:
        """
        Verify code and create session. Creates user if doesn't exist.

        Args:
            data: Verify code request data
            request: FastAPI request object

        Returns:
            Tuple of (session_token, session, user)

        Raises:
            InvalidVerificationCodeError: If code is invalid
            VerificationCodeExpiredError: If code is expired
            TooManyAttemptsError: If too many failed attempts
            CodeAlreadyUsedError: If code was already used
        """
        contact = data.contact
        code_hash = hash_verification_code(data.code)

        verification = await VerificationCode.filter(
            contact=contact,
            code_hash=code_hash
        ).order_by('-created_at').first()

        if not verification:
            await AuthService._increment_failed_attempts(contact)
            raise InvalidVerificationCodeError()

        if verification.is_used:
            raise CodeAlreadyUsedError()

        if verification.is_expired():
            raise VerificationCodeExpiredError()

        if verification.attempts >= AuthService.MAX_ATTEMPTS:
            raise TooManyAttemptsError()

        contact_type = verification.contact_type
        user = await AuthService._get_or_create_user(contact, contact_type)

        verification.is_used = True
        await verification.save()

        session_token, session = await AuthService.create_session(user, request)

        return session_token, session, user

    @staticmethod
    async def _get_or_create_user(contact: str, contact_type: str) -> User:
        """
        Get existing user or create new one.

        Args:
            contact: Email or phone
            contact_type: Type of contact ('email' or 'phone')

        Returns:
            User instance
        """
        if contact_type == 'email':
            user = await User.get_or_none(email=contact)
            if not user:
                user = await User.create(
                    email=contact,
                    is_verified=True
                )
        else:
            user = await User.get_or_none(phone=contact)
            if not user:
                user = await User.create(
                    phone=contact,
                    is_verified=True
                )

        return user

    @staticmethod
    async def _increment_failed_attempts(contact: str) -> None:
        """
        Increment failed attempts for contact.

        Args:
            contact: Email or phone
        """
        recent_codes = await VerificationCode.filter(
            contact=contact,
            is_used=False
        ).order_by('-created_at').limit(5)

        for code in recent_codes:
            code.attempts += 1
            await code.save()

    @staticmethod
    async def create_session(
        user: User,
        request: Request
    ) -> tuple[str, Session]:
        """
        Create a new session for user.

        Args:
            user: User to create session for
            request: FastAPI request object

        Returns:
            Tuple of (session_token, session_instance)
        """
        session_token = generate_session_id()
        session_token_hash = hash_session_id(session_token)

        user_agent = request.headers.get("user-agent")
        ip_address = request.client.host if request.client else None

        session = await Session.create(
            user=user,
            session_token_hash=session_token_hash,
            expires_at=get_session_expiry(),
            user_agent=user_agent,
            ip_address=ip_address
        )

        return session_token, session

    @staticmethod
    async def get_session_by_token(session_token: str) -> Session:
        """
        Get session by token.

        Args:
            session_token: Session token

        Returns:
            Session instance

        Raises:
            InvalidSessionError: If session doesn't exist
            SessionExpiredError: If session is expired
        """
        session_token_hash = hash_session_id(session_token)

        session = await Session.get_or_none(
            session_token_hash=session_token_hash
        ).prefetch_related("user")

        if not session:
            raise InvalidSessionError()

        if session.is_expired():
            await session.delete()
            raise SessionExpiredError()

        session.last_activity = get_current_utc_time()
        await session.save()

        return session

    @staticmethod
    async def get_current_user(session_token: Optional[str]) -> User:
        """
        Get current user from session token.

        Args:
            session_token: Session token from cookie

        Returns:
            Current user instance

        Raises:
            InvalidSessionError: If session is invalid
            UserNotActiveError: If user is not active
        """
        if not session_token:
            raise InvalidSessionError("No session token provided")

        session = await AuthService.get_session_by_token(session_token)

        if not session.user.is_active:
            raise UserNotActiveError()

        return session.user

    @staticmethod
    async def logout(session_token: str) -> None:
        """
        Logout user by deleting session.

        Args:
            session_token: Session token to invalidate
        """
        session_token_hash = hash_session_id(session_token)
        session = await Session.get_or_none(session_token_hash=session_token_hash)

        if session:
            await session.delete()

    @staticmethod
    async def cleanup_expired_sessions() -> int:
        """
        Delete all expired sessions.

        Returns:
            Number of deleted sessions
        """
        now = get_current_utc_time()
        expired_sessions = await Session.filter(expires_at__lt=now)
        count = len(expired_sessions)

        for session in expired_sessions:
            await session.delete()

        return count

    @staticmethod
    async def cleanup_expired_codes() -> int:
        """
        Delete all expired verification codes.

        Returns:
            Number of deleted codes
        """
        now = get_current_utc_time()
        expired_codes = await VerificationCode.filter(expires_at__lt=now)
        count = len(expired_codes)

        for code in expired_codes:
            await code.delete()

        return count