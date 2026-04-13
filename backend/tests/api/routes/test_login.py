from fastapi.testclient import TestClient
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.crud import create_user
from app.models import RefreshToken, User, UserCreate
from tests.utils.utils import random_email, random_lower_string


def test_get_access_token(client: TestClient) -> None:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    tokens = r.json()
    assert r.status_code == 200
    assert "access_token" in tokens
    assert tokens["access_token"]


def test_get_access_token_incorrect_password(client: TestClient) -> None:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": "incorrect",
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert r.status_code == 400


def test_use_access_token(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers=superuser_token_headers,
    )
    result = r.json()
    assert r.status_code == 200
    assert "email" in result


def test_login_with_bcrypt_password_upgrades_to_argon2(
    client: TestClient, db: Session
) -> None:
    """Test that logging in with a bcrypt password hash upgrades it to argon2."""
    email = random_email()
    password = random_lower_string()

    # Create a bcrypt hash directly (simulating legacy password)
    bcrypt_hasher = BcryptHasher()
    bcrypt_hash = bcrypt_hasher.hash(password)
    assert bcrypt_hash.startswith("$2")  # bcrypt hashes start with $2

    user = User(email=email, hashed_password=bcrypt_hash, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.hashed_password.startswith("$2")

    login_data = {"username": email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert r.status_code == 200
    tokens = r.json()
    assert "access_token" in tokens

    db.refresh(user)

    # Verify the hash was upgraded to argon2
    assert user.hashed_password.startswith("$argon2")

    verified, updated_hash = verify_password(password, user.hashed_password)
    assert verified
    # Should not need another update since it's already argon2
    assert updated_hash is None


def test_login_sets_httponly_cookies(client: TestClient) -> None:
    """Login must set httpOnly access_token and refresh_token cookies."""
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert r.status_code == 200

    cookies = r.cookies
    assert "access_token" in cookies
    assert "refresh_token" in cookies
    assert "session" in cookies

    # FastAPI TestClient exposes raw Set-Cookie headers for attribute inspection
    raw_headers = r.headers.get_list("set-cookie")
    at_header = next(h for h in raw_headers if "access_token=" in h)
    rt_header = next(h for h in raw_headers if "refresh_token=" in h)
    session_header = next(h for h in raw_headers if "session=" in h)

    assert "HttpOnly" in at_header
    assert "HttpOnly" in rt_header
    # session cookie must NOT be httpOnly (JS needs to read it)
    assert "HttpOnly" not in session_header


def test_access_token_via_cookie(client: TestClient) -> None:
    """Endpoints accept the access token from the cookie (no Authorization header)."""
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    login_r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert login_r.status_code == 200

    # Use cookie jar from login response — no explicit header needed
    r = client.post(f"{settings.API_V1_STR}/login/test-token")
    assert r.status_code == 200
    assert "email" in r.json()


def test_refresh_token_rotation(client: TestClient) -> None:
    """POST /login/refresh issues a new access token and rotates the refresh token."""
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    login_r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert login_r.status_code == 200
    old_refresh = login_r.cookies.get("refresh_token")

    refresh_r = client.post(f"{settings.API_V1_STR}/login/refresh")
    assert refresh_r.status_code == 200
    assert "access_token" in refresh_r.json()

    new_refresh = refresh_r.cookies.get("refresh_token")
    # Token must have been rotated
    assert new_refresh is not None
    assert new_refresh != old_refresh


def test_refresh_without_cookie_returns_401(client: TestClient) -> None:
    """POST /login/refresh without a cookie must return 401."""
    # Fresh client with no cookies
    with TestClient(client.app) as fresh:
        r = fresh.post(f"{settings.API_V1_STR}/login/refresh")
    assert r.status_code == 401


def test_logout_clears_cookies_and_invalidates_refresh(
    client: TestClient, db: Session
) -> None:
    """Logout deletes the DB refresh token record and clears all auth cookies."""
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    login_r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert login_r.status_code == 200

    # Grab the superuser's ID to scope the DB assertion
    superuser = db.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    assert superuser is not None

    logout_r = client.post(f"{settings.API_V1_STR}/login/logout")
    assert logout_r.status_code == 200

    # After logout the refresh token for this user must be gone
    db.expire_all()  # force re-read from DB
    record = db.exec(
        select(RefreshToken).where(RefreshToken.user_id == superuser.id)
    ).first()
    assert record is None

    # Attempting to refresh after logout must fail
    refresh_r = client.post(f"{settings.API_V1_STR}/login/refresh")
    assert refresh_r.status_code == 401


def test_login_with_argon2_password_keeps_hash(client: TestClient, db: Session) -> None:
    """Test that logging in with an argon2 password hash does not update it."""
    email = random_email()
    password = random_lower_string()

    # Create an argon2 hash (current default)
    argon2_hash = get_password_hash(password)
    assert argon2_hash.startswith("$argon2")

    # Create user with argon2 hash
    user = User(email=email, hashed_password=argon2_hash, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    original_hash = user.hashed_password

    login_data = {"username": email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert r.status_code == 200
    tokens = r.json()
    assert "access_token" in tokens

    db.refresh(user)

    assert user.hashed_password == original_hash
    assert user.hashed_password.startswith("$argon2")


def test_admin_reset_user_password(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Admin can reset a user's password via POST /users/{user_id}/reset-password."""
    email = random_email()
    old_password = random_lower_string()
    new_password = random_lower_string()

    user = create_user(
        session=db,
        user_create=UserCreate(email=email, password=old_password),
    )

    r = client.post(
        f"{settings.API_V1_STR}/users/{user.id}/reset-password",
        headers=superuser_token_headers,
        json={"new_password": new_password},
    )
    assert r.status_code == 200
    assert r.json() == {"message": "Password reset successfully"}

    db.refresh(user)
    verified, _ = verify_password(new_password, user.hashed_password)
    assert verified


def test_non_admin_cannot_reset_password(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    """Non-admin cannot reset another user's password."""
    email = random_email()
    user = create_user(
        session=db,
        user_create=UserCreate(email=email, password=random_lower_string()),
    )
    r = client.post(
        f"{settings.API_V1_STR}/users/{user.id}/reset-password",
        headers=normal_user_token_headers,
        json={"new_password": "newpassword123"},
    )
    assert r.status_code == 403


def test_reset_password_user_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """404 when user does not exist."""
    import uuid

    r = client.post(
        f"{settings.API_V1_STR}/users/{uuid.uuid4()}/reset-password",
        headers=superuser_token_headers,
        json={"new_password": "newpassword123"},
    )
    assert r.status_code == 404


def test_reset_password_too_short(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """422 when new password is too short."""
    user = create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )
    r = client.post(
        f"{settings.API_V1_STR}/users/{user.id}/reset-password",
        headers=superuser_token_headers,
        json={"new_password": "short"},
    )
    assert r.status_code == 422
