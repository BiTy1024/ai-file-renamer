import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import EmailStr
from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlmodel import Column, Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, Enum):  # noqa: SLOT000
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    role: UserRole = Field(default=UserRole.VIEWER)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    role: UserRole = Field(
        default=UserRole.VIEWER,
        sa_column=Column(SAEnum(UserRole), nullable=False, default=UserRole.VIEWER),
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


# --- Service Account models ---


class ServiceAccountBase(SQLModel):
    display_name: str = Field(max_length=255)
    description: str | None = Field(default=None, max_length=500)


class ServiceAccountCreate(ServiceAccountBase):
    credentials_json: str
    user_id: uuid.UUID


class ServiceAccountUpdate(SQLModel):
    display_name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    credentials_json: str | None = None
    user_id: uuid.UUID | None = None


class ServiceAccount(ServiceAccountBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    encrypted_credentials: str
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, unique=True, ondelete="CASCADE"
    )
    user: User | None = Relationship()
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class ServiceAccountPublic(ServiceAccountBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime | None = None


class ServiceAccountPublicWithEmail(ServiceAccountPublic):
    client_email: str | None = None


class ServiceAccountsPublic(SQLModel):
    data: list[ServiceAccountPublic]
    count: int
