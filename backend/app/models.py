import uuid
from datetime import datetime, timezone
from enum import Enum

import sqlalchemy as sa
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


# --- Refresh token model ---


class RefreshToken(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, index=True, ondelete="CASCADE"
    )
    token_hash: str = Field(max_length=64, unique=True)  # sha256 hex digest
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))  # type: ignore
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


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


class DriveFolderSearchResult(SQLModel):
    id: str
    name: str
    parent_name: str | None = None


class DriveFolderSearchResultList(SQLModel):
    results: list[DriveFolderSearchResult]


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
    max_requests_per_day: int | None = Field(default=None, ge=1)
    max_tokens_per_month: int | None = Field(default=None, ge=1)


class UserLimitUpdate(SQLModel):
    max_requests_per_day: int | None = Field(default=None, ge=1)
    max_tokens_per_month: int | None = Field(default=None, ge=1)


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
    original_name: str = ""


class RenameConfirmRequest(SQLModel):
    folder_id: str
    renames: list[RenameConfirmItem]


class RenameResult(SQLModel):
    file_id: str
    success: bool
    error: str | None = None


class RenameConfirmResponse(SQLModel):
    results: list[RenameResult]


# --- Convention preset models ---


class ConventionPresetBase(SQLModel):
    name: str = Field(max_length=255)
    convention: str = Field(max_length=500)
    description: str | None = Field(default=None, max_length=500)
    content_type: str | None = Field(default=None, max_length=100)


class ConventionPresetCreate(ConventionPresetBase):
    pass


class ConventionPresetUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=255)
    convention: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=500)
    content_type: str | None = Field(default=None, max_length=100)


class ConventionPreset(ConventionPresetBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class ConventionPresetPublic(ConventionPresetBase):
    id: uuid.UUID
    created_at: datetime | None = None


class ConventionPresetsPublic(SQLModel):
    data: list[ConventionPresetPublic]
    count: int


# --- Rename history models ---


class RenameLog(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    folder_id: str = Field(max_length=255)
    original_name: str = Field(max_length=500)
    new_name: str = Field(max_length=500)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class RenameLogPublic(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    folder_id: str
    original_name: str
    new_name: str
    created_at: datetime | None = None


class RenameHistoryResponse(SQLModel):
    data: list[RenameLogPublic]
    count: int


# --- Activity log models ---


class ActivityAction(str, Enum):  # noqa: SLOT000
    LOGIN = "login"
    LOGOUT = "logout"
    RENAME = "rename"
    SETTINGS_CHANGE = "settings_change"
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    LIMIT_CHANGED = "limit_changed"
    API_KEY_CHANGED = "api_key_changed"


class ActivityLog(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    action: ActivityAction = Field(
        sa_column=Column(
            SAEnum(
                ActivityAction,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
        )
    )
    detail: str | None = Field(default=None, max_length=1000)
    tokens_used: int | None = None
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class ActivityLogPublic(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str | None = None
    action: ActivityAction
    detail: str | None = None
    tokens_used: int | None = None
    created_at: datetime | None = None


class ActivityLogResponse(SQLModel):
    data: list[ActivityLogPublic]
    count: int


# --- Admin settings models ---


class AdminSetting(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    key: str = Field(max_length=100, unique=True, index=True)
    value: str = Field(max_length=2000)
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class AdminSettingsPublic(SQLModel):
    default_max_requests_per_day: int | None = None
    default_max_tokens_per_month: int | None = None
    monthly_spend_threshold: int | None = None


class AdminSettingsUpdate(SQLModel):
    default_max_requests_per_day: int | None = Field(default=None, ge=1)
    default_max_tokens_per_month: int | None = Field(default=None, ge=1)
    monthly_spend_threshold: int | None = Field(default=None, ge=1)


# --- Admin usage response models ---


class UsageSummaryAdmin(SQLModel):
    current_month_tokens: int
    previous_month_tokens: int
    all_time_tokens: int
    current_month_cost: float
    previous_month_cost: float
    all_time_cost: float


class UsageTimeseriesPoint(SQLModel):
    date: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    request_count: int


class ApiKeyStatus(SQLModel):
    is_set: bool
    masked_key: str | None = None
    source: str = "not_configured"  # "env", "database", "not_configured"


# --- Alert models ---


class AlertType(str, Enum):  # noqa: SLOT000
    USER_80_PCT = "user_80_pct"
    USER_100_PCT = "user_100_pct"
    GLOBAL_SPEND = "global_spend"


class AlertRecord(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    alert_type: AlertType = Field(
        sa_column=Column(
            SAEnum(
                AlertType,
                values_callable=lambda e: [m.value for m in e],
            ),
            nullable=False,
        )
    )
    period: str = Field(max_length=7)  # "YYYY-MM"
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    __table_args__ = (sa.UniqueConstraint("user_id", "alert_type", "period"),)


class AlertRecordPublic(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str | None = None
    alert_type: AlertType
    period: str
    created_at: datetime | None = None


class AlertHistoryResponse(SQLModel):
    data: list[AlertRecordPublic]
    count: int
