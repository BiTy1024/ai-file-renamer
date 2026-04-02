from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm

from app import crud
from app.api.deps import CurrentUser, SessionDep, require_role
from app.core import security
from app.core.config import settings
from app.core.limiter import limiter
from app.models import Message, NewPassword, Token, UserPublic, UserRole, UserUpdate
from app.models import User as UserModel
from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
)

router = APIRouter(tags=["login"])

_ACCESS_MAX_AGE = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
_REFRESH_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400


def _set_auth_cookies(
    response: Response, access_token: str, refresh_token: str
) -> None:
    """Set access_token and refresh_token as httpOnly cookies plus a plain session flag."""
    secure = settings.cookie_secure
    response.set_cookie(
        "access_token",
        access_token,
        max_age=_ACCESS_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=secure,
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        max_age=_REFRESH_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=secure,
    )
    # Non-httpOnly flag so JS can detect login state without reading the JWT
    response.set_cookie(
        "session",
        "1",
        max_age=_ACCESS_MAX_AGE,
        samesite="lax",
        secure=settings.cookie_secure,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", samesite="lax")
    response.delete_cookie("refresh_token", samesite="lax")
    response.delete_cookie("session", samesite="lax")


@router.post("/login/access-token")
@limiter.limit("5/minute")
def login_access_token(
    request: Request,  # noqa: ARG001 — required by slowapi rate limiter
    response: Response,
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """
    OAuth2 compatible token login. Sets httpOnly cookies and returns token JSON.
    """
    user = crud.authenticate(
        session=session, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = security.create_access_token(
        user.id, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = security.create_refresh_token(session, user.id)
    _set_auth_cookies(response, access_token, refresh_token)
    return Token(access_token=access_token)


@router.post("/login/refresh")
def refresh_access_token(
    request: Request, response: Response, session: SessionDep
) -> Token:
    """
    Issue a new access token using the refresh token cookie (rotates the refresh token).
    """
    raw_refresh = request.cookies.get("refresh_token")
    if not raw_refresh:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    user_id = security.verify_and_rotate_refresh_token(session, raw_refresh)
    if not user_id:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = session.get(UserModel, user_id)
    if not user or not user.is_active:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="User not found or inactive")

    access_token = security.create_access_token(
        user.id, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    new_refresh_token = security.create_refresh_token(session, user.id)
    _set_auth_cookies(response, access_token, new_refresh_token)
    return Token(access_token=access_token)


@router.post("/login/logout")
def logout(request: Request, response: Response, session: SessionDep) -> Message:
    """
    Invalidate the refresh token and clear all auth cookies.
    """
    raw_refresh = request.cookies.get("refresh_token")
    if raw_refresh:
        security.delete_refresh_token(session, raw_refresh)
    _clear_auth_cookies(response)
    return Message(message="Logged out successfully")


@router.post("/login/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    """
    Test access token
    """
    return current_user


@router.post("/password-recovery/{email}")
def recover_password(email: str, session: SessionDep) -> Message:
    """
    Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    # Always return the same response to prevent email enumeration attacks
    # Only send email if user actually exists
    if user:
        password_reset_token = generate_password_reset_token(email=email)
        email_data = generate_reset_password_email(
            email_to=user.email, email=email, token=password_reset_token
        )
        send_email(
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return Message(
        message="If that email is registered, we sent a password recovery link"
    )


@router.post("/reset-password/")
def reset_password(session: SessionDep, body: NewPassword) -> Message:
    """
    Reset password
    """
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = crud.get_user_by_email(session=session, email=email)
    if not user:
        # Don't reveal that the user doesn't exist - use same error as invalid token
        raise HTTPException(status_code=400, detail="Invalid token")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    user_in_update = UserUpdate(password=body.new_password)
    crud.update_user(
        session=session,
        db_user=user,
        user_in=user_in_update,
    )
    return Message(message="Password updated successfully")


@router.post(
    "/password-recovery-html-content/{email}",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    response_class=HTMLResponse,
)
def recover_password_html_content(email: str, session: SessionDep) -> Any:
    """
    HTML Content for Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )

    return HTMLResponse(
        content=email_data.html_content, headers={"subject:": email_data.subject}
    )
