import json
import uuid
from typing import Any

from sqlmodel import Session, select

from app.core.security import (
    decrypt_text,
    encrypt_text,
    get_password_hash,
    verify_password,
)
from app.models import (
    ServiceAccount,
    ServiceAccountCreate,
    ServiceAccountUpdate,
    User,
    UserCreate,
    UserUpdate,
)


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


# Dummy hash to use for timing attack prevention when user is not found
# This is an Argon2 hash of a random password, used to ensure constant-time comparison
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"


# --- Service Account CRUD ---

REQUIRED_SA_FIELDS = {"type", "project_id", "private_key", "client_email"}


def validate_sa_credentials(credentials_json: str) -> dict[str, Any]:
    try:
        data = json.loads(credentials_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("Credentials must be a JSON object")
    if data.get("type") != "service_account":
        raise ValueError("Credentials 'type' must be 'service_account'")
    missing = REQUIRED_SA_FIELDS - data.keys()
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")
    return data


def create_service_account(
    *, session: Session, sa_create: ServiceAccountCreate
) -> ServiceAccount:
    creds = validate_sa_credentials(sa_create.credentials_json)
    encrypted = encrypt_text(json.dumps(creds))
    db_obj = ServiceAccount(
        display_name=sa_create.display_name,
        description=sa_create.description,
        encrypted_credentials=encrypted,
        user_id=sa_create.user_id,
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_service_account_by_user_id(
    *, session: Session, user_id: uuid.UUID
) -> ServiceAccount | None:
    statement = select(ServiceAccount).where(ServiceAccount.user_id == user_id)
    return session.exec(statement).first()


def get_service_account_client_email(sa: ServiceAccount) -> str | None:
    try:
        creds = json.loads(decrypt_text(sa.encrypted_credentials))
        result: str | None = creds.get("client_email")
        return result
    except Exception:
        return None


def update_service_account(
    *, session: Session, db_sa: ServiceAccount, sa_in: ServiceAccountUpdate
) -> ServiceAccount:
    update_data = sa_in.model_dump(exclude_unset=True)
    if "credentials_json" in update_data and update_data["credentials_json"]:
        creds = validate_sa_credentials(update_data.pop("credentials_json"))
        db_sa.encrypted_credentials = encrypt_text(json.dumps(creds))
    else:
        update_data.pop("credentials_json", None)
    db_sa.sqlmodel_update(update_data)
    session.add(db_sa)
    session.commit()
    session.refresh(db_sa)
    return db_sa


def delete_service_account(*, session: Session, db_sa: ServiceAccount) -> None:
    session.delete(db_sa)
    session.commit()


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        # Prevent timing attacks by running password verification even when user doesn't exist
        # This ensures the response time is similar whether or not the email exists
        verify_password(password, DUMMY_HASH)
        return None
    verified, updated_password_hash = verify_password(password, db_user.hashed_password)
    if not verified:
        return None
    if updated_password_hash:
        db_user.hashed_password = updated_password_hash
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    return db_user
