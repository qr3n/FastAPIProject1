# app/api/v1/endpoints/auth.py
from fastapi import APIRouter, HTTPException, status, Response, Request, Depends
from typing import List

from app.schemas.user import (
    SendCodeSchema,
    VerifyCodeSchema,
    UserResponseSchema,
    SessionInfoSchema
)
from app.services.auth_service import AuthService
from app.api.v1.dependencies.auth import get_current_user, get_session_token
from shared.models.user import User
from app.core.config import settings
from app.exceptions.auth_exceptions import (
    InvalidVerificationCodeError,
    VerificationCodeExpiredError,
    TooManyAttemptsError,
    CodeAlreadyUsedError,
    RateLimitError
)

router = APIRouter(prefix="/auth", tags=["authentication"])


def set_session_cookie(response: Response, session_token: str) -> None:
    """Set session cookie in response."""
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_token,
        max_age=settings.SESSION_MAX_AGE,
        httponly=settings.SESSION_COOKIE_HTTPONLY,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        domain=settings.SESSION_COOKIE_DOMAIN
    )


def clear_session_cookie(response: Response) -> None:
    """Clear session cookie from response."""
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        domain=settings.SESSION_COOKIE_DOMAIN
    )


@router.post("/send-code", status_code=status.HTTP_200_OK, operation_id="sendCode")
async def send_code(data: SendCodeSchema) -> dict:
    """Send verification code to email or phone."""
    try:
        return await AuthService.send_verification_code(data)
    except RateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )


@router.post("/verify-code", response_model=UserResponseSchema, operation_id="verifyCode")
async def verify_code(
    data: VerifyCodeSchema,
    request: Request,
    response: Response
) -> UserResponseSchema:
    """Verify code and login. Creates user if doesn't exist."""
    try:
        session_token, _, user = await AuthService.verify_code_and_login(data, request)
        set_session_cookie(response, session_token)
        return UserResponseSchema.from_orm_user(user)
    except (
        InvalidVerificationCodeError,
        VerificationCodeExpiredError,
        CodeAlreadyUsedError
    ) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except TooManyAttemptsError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, operation_id="logout")
async def logout(
    response: Response,
    session_token: str = Depends(get_session_token)
) -> None:
    """Logout user by invalidating session."""
    await AuthService.logout(session_token)
    clear_session_cookie(response)


@router.get("/me", response_model=UserResponseSchema, operation_id="getCurrentUser")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> UserResponseSchema:
    """Get current user information."""
    return UserResponseSchema.from_orm_user(current_user)


@router.get("/sessions", response_model=List[SessionInfoSchema], operation_id="getUserSessions")
async def get_user_sessions(
    current_user: User = Depends(get_current_user)
) -> List[SessionInfoSchema]:
    """Get all active sessions for current user."""
    sessions = await current_user.sessions.all()
    return [SessionInfoSchema.from_orm_session(session) for session in sessions]


@router.delete("/sessions/{sid}", status_code=status.HTTP_204_NO_CONTENT, operation_id="deleteSession")
async def delete_session(
    sid: str,
    current_user: User = Depends(get_current_user)
) -> None:
    """Delete a specific session."""
    from shared.models.user import Session

    session = await Session.get_or_none(id=sid, user=current_user)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    await session.delete()