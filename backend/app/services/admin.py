import csv
import io
import uuid
from collections.abc import Generator
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, col, func, select

from app.core.config import settings
from app.core.security import decrypt_text, encrypt_text
from app.models import (
    ActivityAction,
    ActivityLog,
    ActivityLogPublic,
    AdminSetting,
    AdminSettingsPublic,
    ApiKeyStatus,
    RenameLog,
    RenameLogPublic,
    UsageRecord,
    UsageSummaryAdmin,
    UsageTimeseriesPoint,
    User,
)

# Pricing per 1M tokens (USD).
# Update when Anthropic changes pricing or new models are added.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
}

DEFAULT_PRICING = {"input": 3.0, "output": 15.0}


def _calculate_cost(input_tokens: int, output_tokens: int, model: str = "") -> float:
    pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
    return (
        input_tokens * pricing["input"] + output_tokens * pricing["output"]
    ) / 1_000_000


def _month_start(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_usage_summary(session: Session) -> UsageSummaryAdmin:
    now = datetime.now(timezone.utc)
    current_month = _month_start(now)
    previous_month = _month_start(current_month - timedelta(days=1))

    def _aggregate(start: datetime | None, end: datetime | None) -> tuple[int, float]:
        stmt = select(
            func.coalesce(func.sum(UsageRecord.input_tokens), 0),
            func.coalesce(func.sum(UsageRecord.output_tokens), 0),
        )
        if start:
            stmt = stmt.where(UsageRecord.created_at >= start)  # type: ignore[arg-type]
        if end:
            stmt = stmt.where(UsageRecord.created_at < end)  # type: ignore[arg-type]
        row = session.exec(stmt).one()
        inp, out = int(row[0]), int(row[1])  # type: ignore[index]
        return inp + out, _calculate_cost(inp, out)

    cur_tokens, cur_cost = _aggregate(current_month, None)
    prev_tokens, prev_cost = _aggregate(previous_month, current_month)
    all_tokens, all_cost = _aggregate(None, None)

    return UsageSummaryAdmin(
        current_month_tokens=cur_tokens,
        previous_month_tokens=prev_tokens,
        all_time_tokens=all_tokens,
        current_month_cost=round(cur_cost, 4),
        previous_month_cost=round(prev_cost, 4),
        all_time_cost=round(all_cost, 4),
    )


def get_usage_timeseries(
    session: Session,
    period: str = "daily",
    range_days: int = 30,
    user_id: uuid.UUID | None = None,
) -> list[UsageTimeseriesPoint]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=range_days)

    trunc_map = {"daily": "day", "weekly": "week", "monthly": "month"}
    trunc = trunc_map.get(period, "day")

    date_col = func.date_trunc(trunc, UsageRecord.created_at).label("bucket")

    stmt = (
        select(
            date_col,
            func.coalesce(func.sum(UsageRecord.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(UsageRecord.output_tokens), 0).label(
                "output_tokens"
            ),
            func.count().label("request_count"),
        )
        .where(UsageRecord.created_at >= start)  # type: ignore[arg-type]
        .group_by(date_col)
        .order_by(date_col)
    )

    if user_id:
        stmt = stmt.where(UsageRecord.user_id == user_id)

    rows = session.exec(stmt).all()
    points = []
    for row in rows:
        inp = int(row[1])  # type: ignore[index]
        out = int(row[2])  # type: ignore[index]
        points.append(
            UsageTimeseriesPoint(
                date=row[0].strftime("%Y-%m-%d") if row[0] else "",  # type: ignore[index]
                input_tokens=inp,
                output_tokens=out,
                total_tokens=inp + out,
                cost=round(_calculate_cost(inp, out), 4),
                request_count=int(row[3]),  # type: ignore[index]
            )
        )
    return points


def parse_range(range_str: str) -> int:
    """Convert '30d', '90d', '1y' to days."""
    if range_str.endswith("y"):
        return int(range_str[:-1]) * 365
    if range_str.endswith("d"):
        return int(range_str[:-1])
    return 30


# --- Activity log ---


def log_activity(
    session: Session,
    user_id: uuid.UUID,
    action: ActivityAction,
    detail: str | None = None,
    tokens_used: int | None = None,
) -> ActivityLog:
    entry = ActivityLog(
        user_id=user_id,
        action=action,
        detail=detail,
        tokens_used=tokens_used,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def get_activity_log(
    session: Session,
    skip: int = 0,
    limit: int = 50,
    user_id: uuid.UUID | None = None,
    action: ActivityAction | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> tuple[list[ActivityLogPublic], int]:
    stmt = select(ActivityLog, User.email).join(User, ActivityLog.user_id == User.id)  # type: ignore[arg-type]
    count_stmt = select(func.count()).select_from(ActivityLog)

    if user_id:
        stmt = stmt.where(ActivityLog.user_id == user_id)
        count_stmt = count_stmt.where(ActivityLog.user_id == user_id)
    if action:
        stmt = stmt.where(ActivityLog.action == action)  # type: ignore[arg-type]
        count_stmt = count_stmt.where(ActivityLog.action == action)  # type: ignore[arg-type]
    if from_date:
        stmt = stmt.where(ActivityLog.created_at >= from_date)  # type: ignore[arg-type]
        count_stmt = count_stmt.where(ActivityLog.created_at >= from_date)  # type: ignore[arg-type]
    if to_date:
        stmt = stmt.where(ActivityLog.created_at <= to_date)  # type: ignore[arg-type]
        count_stmt = count_stmt.where(ActivityLog.created_at <= to_date)  # type: ignore[arg-type]

    count = session.exec(count_stmt).one()
    stmt = stmt.order_by(col(ActivityLog.created_at).desc()).offset(skip).limit(limit)

    rows = session.exec(stmt).all()
    entries = []
    for row in rows:
        log_entry = row[0]  # type: ignore[index]
        email = row[1]  # type: ignore[index]
        entries.append(
            ActivityLogPublic(
                id=log_entry.id,
                user_id=log_entry.user_id,
                user_email=email,
                action=log_entry.action,
                detail=log_entry.detail,
                tokens_used=log_entry.tokens_used,
                created_at=log_entry.created_at,
            )
        )
    return entries, count


def export_activity_csv(
    session: Session,
    user_id: uuid.UUID | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    max_rows: int = 10_000,
) -> Generator[str, None, None]:
    stmt = select(ActivityLog, User.email).join(User, ActivityLog.user_id == User.id)  # type: ignore[arg-type]

    if user_id:
        stmt = stmt.where(ActivityLog.user_id == user_id)
    if from_date:
        stmt = stmt.where(ActivityLog.created_at >= from_date)  # type: ignore[arg-type]
    if to_date:
        stmt = stmt.where(ActivityLog.created_at <= to_date)  # type: ignore[arg-type]

    stmt = stmt.order_by(col(ActivityLog.created_at).desc()).limit(max_rows)

    # Header
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["timestamp", "user_email", "action", "detail", "tokens_used"])
    yield buf.getvalue()
    buf.truncate(0)
    buf.seek(0)

    # Stream rows one at a time
    result = session.exec(stmt)
    for row in result:
        log_entry = row[0]  # type: ignore[index]
        email = row[1]  # type: ignore[index]
        writer.writerow(
            [
                log_entry.created_at.isoformat() if log_entry.created_at else "",
                email,
                log_entry.action.value if log_entry.action else "",
                log_entry.detail or "",
                log_entry.tokens_used or "",
            ]
        )
        yield buf.getvalue()
        buf.truncate(0)
        buf.seek(0)


# --- API key management ---


_API_KEY_SETTING = "claude_api_key"


def get_api_key_status(session: Session) -> ApiKeyStatus:
    # Check env var first
    if settings.CLAUDE_API_KEY:
        key = settings.CLAUDE_API_KEY
        masked = key[:7] + "..." + key[-4:] if len(key) > 11 else "***"
        return ApiKeyStatus(is_set=True, masked_key=masked, source="env")

    # Check database
    setting = session.exec(
        select(AdminSetting).where(AdminSetting.key == _API_KEY_SETTING)
    ).first()
    if setting:
        try:
            key = decrypt_text(setting.value)
            masked = key[:7] + "..." + key[-4:] if len(key) > 11 else "***"
            return ApiKeyStatus(is_set=True, masked_key=masked, source="database")
        except Exception:
            return ApiKeyStatus(is_set=False, source="not_configured")

    return ApiKeyStatus(is_set=False, source="not_configured")


def set_api_key(session: Session, api_key: str) -> None:
    encrypted = encrypt_text(api_key)
    setting = session.exec(
        select(AdminSetting).where(AdminSetting.key == _API_KEY_SETTING)
    ).first()
    if setting:
        setting.value = encrypted
        setting.updated_at = datetime.now(timezone.utc)
    else:
        setting = AdminSetting(key=_API_KEY_SETTING, value=encrypted)
    session.add(setting)
    session.commit()


def get_active_api_key(session: Session) -> str | None:
    """Return the active Claude API key (env var takes precedence over DB)."""
    if settings.CLAUDE_API_KEY:
        return settings.CLAUDE_API_KEY
    db_setting = session.exec(
        select(AdminSetting).where(AdminSetting.key == _API_KEY_SETTING)
    ).first()
    if db_setting:
        try:
            return decrypt_text(db_setting.value)
        except Exception:
            return None
    return None


def delete_api_key(session: Session) -> None:
    setting = session.exec(
        select(AdminSetting).where(AdminSetting.key == _API_KEY_SETTING)
    ).first()
    if setting:
        session.delete(setting)
        session.commit()


# --- Admin settings (global defaults) ---


_SETTINGS_KEYS = [
    "default_max_requests_per_day",
    "default_max_tokens_per_month",
    "monthly_spend_threshold",
]


def get_admin_settings(session: Session) -> AdminSettingsPublic:
    settings_map: dict[str, str] = {}
    rows = session.exec(
        select(AdminSetting).where(
            AdminSetting.key.in_(_SETTINGS_KEYS)  # type: ignore[union-attr]
        )
    ).all()
    for row in rows:
        settings_map[row.key] = row.value

    return AdminSettingsPublic(
        default_max_requests_per_day=int(settings_map["default_max_requests_per_day"])
        if "default_max_requests_per_day" in settings_map
        else None,
        default_max_tokens_per_month=int(settings_map["default_max_tokens_per_month"])
        if "default_max_tokens_per_month" in settings_map
        else None,
        monthly_spend_threshold=int(settings_map["monthly_spend_threshold"])
        if "monthly_spend_threshold" in settings_map
        else None,
    )


def update_admin_settings(
    session: Session,
    default_max_requests_per_day: int | None = None,
    default_max_tokens_per_month: int | None = None,
    monthly_spend_threshold: int | None = None,
) -> AdminSettingsPublic:
    now = datetime.now(timezone.utc)
    updates = {
        "default_max_requests_per_day": default_max_requests_per_day,
        "default_max_tokens_per_month": default_max_tokens_per_month,
        "monthly_spend_threshold": monthly_spend_threshold,
    }
    for key, value in updates.items():
        existing = session.exec(
            select(AdminSetting).where(AdminSetting.key == key)
        ).first()
        if value is not None:
            if existing:
                existing.value = str(value)
                existing.updated_at = now
                session.add(existing)
            else:
                session.add(AdminSetting(key=key, value=str(value), updated_at=now))
        elif existing:
            session.delete(existing)
    session.commit()
    return get_admin_settings(session)


# --- Per-user activity (rename history) ---


def get_user_recent_activity(
    session: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 50
) -> tuple[list[RenameLogPublic], int]:
    count_stmt = (
        select(func.count()).select_from(RenameLog).where(RenameLog.user_id == user_id)
    )
    count = session.exec(count_stmt).one()

    stmt = (
        select(RenameLog)
        .where(RenameLog.user_id == user_id)
        .order_by(col(RenameLog.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    rows = session.exec(stmt).all()
    return [
        RenameLogPublic(
            id=r.id,
            user_id=r.user_id,
            folder_id=r.folder_id,
            original_name=r.original_name,
            new_name=r.new_name,
            created_at=r.created_at,
        )
        for r in rows
    ], count
