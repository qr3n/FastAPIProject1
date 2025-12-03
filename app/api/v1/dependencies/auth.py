# app/api/v1/dependencies/auth.py
from typing import Optional
from fastapi import Cookie, Depends, HTTPException, status

from shared.models.user import User
from app.services.auth_service import AuthService
from app.core.config import settings
from app.exceptions.auth_exceptions import (
    InvalidSessionError,
    SessionExpiredError,
    UserNotActiveError
)


async def get_session_token(
        session_id: Optional[str] = Cookie(None, alias=settings.SESSION_COOKIE_NAME)
) -> str:
    """
    Extract session token from cookie.

    Args:
        session_id: Session ID from cookie

    Returns:
        Session token

    Raises:
        HTTPException: If session token is missing
    """
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return session_id


async def get_current_user(
        session_token: str = Depends(get_session_token)
) -> User:
    """
    Get current authenticated user.

    Args:
        session_token: Session token from cookie

    Returns:
        Current user

    Raises:
        HTTPException: If session is invalid or expired
    """
    try:
        return await AuthService.get_current_user(session_token)
    except (InvalidSessionError, SessionExpiredError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except UserNotActiveError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


async def get_optional_current_user(
        session_id: Optional[str] = Cookie(None, alias=settings.SESSION_COOKIE_NAME)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.

    Args:
        session_id: Session ID from cookie

    Returns:
        Current user or None
    """
    if not session_id:
        return None

    try:
        return await AuthService.get_current_user(session_id)
    except Exception:
        return None