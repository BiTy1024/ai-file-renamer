import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from cryptography.fernet import Fernet
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlmodel import Session, select

from app.core.config import settings

password_hash = PasswordHash(
    (
        Argon2Hasher(),
        BcryptHasher(),
    )
)


ALGORITHM = "HS256"


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(
    plain_password: str, hashed_password: str
) -> tuple[bool, str | None]:
    return password_hash.verify_and_update(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def _get_fernet() -> Fernet:
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_text(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_text(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()


# --- Refresh token helpers ---


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_refresh_token(session: Session, user_id: Any) -> str:
    """Generate, store, and return a raw refresh token for the given user.

    Any existing refresh token for this user is replaced (one active token per user).
    """
    from app.models import RefreshToken  # local import to avoid circular deps

    raw = secrets.token_urlsafe(64)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    existing = session.exec(
        select(RefreshToken).where(RefreshToken.user_id == user_id)
    ).first()
    if existing:
        session.delete(existing)

    record = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(raw),
        expires_at=expires_at,
    )
    session.add(record)
    session.commit()
    return raw


def verify_and_rotate_refresh_token(session: Session, raw: str) -> Any:
    """Validate a raw refresh token and return the user_id if valid, else None.

    The old token record is deleted so callers must immediately issue a new one
    (rotation). This prevents replay attacks on stolen refresh tokens.
    """
    from app.models import RefreshToken  # local import to avoid circular deps

    record = session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw))
    ).first()

    if not record:
        return None

    if record.expires_at < datetime.now(timezone.utc):
        session.delete(record)
        session.commit()
        return None

    user_id = record.user_id
    session.delete(record)
    session.commit()
    return user_id


def delete_refresh_token(session: Session, raw: str) -> None:
    """Delete a refresh token by raw value (used on logout)."""
    from app.models import RefreshToken  # local import to avoid circular deps

    record = session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw))
    ).first()
    if record:
        session.delete(record)
        session.commit()
