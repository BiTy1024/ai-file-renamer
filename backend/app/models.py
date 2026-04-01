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


# --- Google Drive response models ---


class DriveFolder(SQLModel):
    id: str
    name: str
    created_time: str | None = None


class DriveFolderList(SQLModel):
    folders: list[DriveFolder]


class DriveFile(SQLModel):
    id: str
    name: str
    mime_type: str
    size: str | None = None
    modified_time: str | None = None
    thumbnail_url: str | None = None


class DriveFileList(SQLModel):
    files: list[DriveFile]


# --- Usage tracking models ---


class UsageRecord(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    input_tokens: int
    output_tokens: int
    model: str = Field(max_length=100)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class UsageRecordPublic(SQLModel):
    id: uuid.UUID
    input_tokens: int
    output_tokens: int
    model: str
    created_at: datetime | None = None


# --- User rate limit models ---


class UserLimit(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, unique=True)
    max_requests_per_day: int | None = None
    max_tokens_per_month: int | None = None


class UserLimitPublic(SQLModel):
    max_requests_per_day: int | None = None
    max_tokens_per_month: int | None = None


class UserLimitUpdate(SQLModel):
    max_requests_per_day: int | None = None
    max_tokens_per_month: int | None = None


class UsageSummary(SQLModel):
    requests_today: int
    tokens_this_month: int
    limit: UserLimitPublic | None = None


# --- Rename models ---


class RenamePreview(SQLModel):
    file_id: str
    original_name: str
    proposed_name: str
    error: str | None = None


class RenamePreviewRequest(SQLModel):
    folder_id: str
    convention: str
    instruction: str | None = None
    content_type: str | None = None


class RenamePreviewResponse(SQLModel):
    previews: list[RenamePreview]


class RenameConfirmItem(SQLModel):
    file_id: str
    new_name: str


class RenameConfirmRequest(SQLModel):
    renames: list[RenameConfirmItem]


class RenameResult(SQLModel):
    file_id: str
    success: bool
    error: str | None = None


class RenameConfirmResponse(SQLModel):
    results: list[RenameResult]
