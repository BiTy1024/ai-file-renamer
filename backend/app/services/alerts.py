import logging
import uuid
from datetime import datetime, timezone

from sqlmodel import Session, col, func, select

from app.core.config import settings
from app.models import (
    AdminSetting,
    AlertRecord,
    AlertRecordPublic,
    AlertType,
    User,
    UserLimit,
)

logger = logging.getLogger(__name__)

_SPEND_THRESHOLD_KEY = "monthly_spend_threshold"


def _current_period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _alert_already_sent(
    session: Session, user_id: uuid.UUID, alert_type: AlertType, period: str
) -> bool:
    stmt = (
        select(func.count())
        .select_from(AlertRecord)
        .where(
            AlertRecord.user_id == user_id,
            AlertRecord.alert_type == alert_type,  # type: ignore[arg-type]
            AlertRecord.period == period,
        )
    )
    return session.exec(stmt).one() > 0


def _record_alert(
    session: Session, user_id: uuid.UUID, alert_type: AlertType, period: str
) -> AlertRecord:
    record = AlertRecord(user_id=user_id, alert_type=alert_type, period=period)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def _send_alert_email(
    admin_email: str,
    user_email: str,
    alert_type: AlertType,
    current_value: int,
    limit_value: int | float,
) -> None:
    """Send an alert email. Fails silently if email is not configured."""
    if not settings.emails_enabled:
        logger.info(
            "Alert %s for %s skipped (email not configured)", alert_type, user_email
        )
        return

    from app.utils import send_email

    subject_map = {
        AlertType.USER_80_PCT: f"Usage alert: {user_email} at 80% of token limit",
        AlertType.USER_100_PCT: f"Usage alert: {user_email} reached token limit",
        AlertType.GLOBAL_SPEND: "Usage alert: Monthly spend threshold exceeded",
    }

    body_map = {
        AlertType.USER_80_PCT: (
            f"<p>User <strong>{user_email}</strong> has used "
            f"<strong>{current_value:,}</strong> of their "
            f"<strong>{limit_value:,}</strong> monthly token limit (80%).</p>"
        ),
        AlertType.USER_100_PCT: (
            f"<p>User <strong>{user_email}</strong> has reached their monthly "
            f"token limit of <strong>{limit_value:,}</strong> tokens. "
            f"Further operations are blocked until the next billing period.</p>"
        ),
        AlertType.GLOBAL_SPEND: (
            f"<p>Total monthly token usage has reached "
            f"<strong>{current_value:,}</strong> tokens, exceeding the "
            f"configured threshold of <strong>{int(limit_value):,}</strong>.</p>"
        ),
    }

    try:
        send_email(
            email_to=admin_email,
            subject=subject_map[alert_type],
            html_content=body_map[alert_type],
        )
    except Exception:
        logger.exception("Failed to send alert email for %s", alert_type)


def check_and_send_alerts(
    session: Session, user_id: uuid.UUID, tokens_this_month: int
) -> None:
    """Check token limits and global spend, send alerts if thresholds crossed."""
    period = _current_period()

    # Get admin email for notifications
    admin = session.exec(select(User).where(User.role == "admin")).first()  # type: ignore[arg-type]
    if not admin:
        return
    admin_email = admin.email

    # Get user info
    user = session.get(User, user_id)
    if not user:
        return
    user_email = user.email

    # --- Per-user limit alerts ---
    limit = session.exec(select(UserLimit).where(UserLimit.user_id == user_id)).first()

    if limit and limit.max_tokens_per_month:
        max_tokens = limit.max_tokens_per_month
        pct = tokens_this_month / max_tokens

        if pct >= 1.0 and not _alert_already_sent(
            session, user_id, AlertType.USER_100_PCT, period
        ):
            _record_alert(session, user_id, AlertType.USER_100_PCT, period)
            _send_alert_email(
                admin_email,
                user_email,
                AlertType.USER_100_PCT,
                tokens_this_month,
                max_tokens,
            )

        elif pct >= 0.8 and not _alert_already_sent(
            session, user_id, AlertType.USER_80_PCT, period
        ):
            _record_alert(session, user_id, AlertType.USER_80_PCT, period)
            _send_alert_email(
                admin_email,
                user_email,
                AlertType.USER_80_PCT,
                tokens_this_month,
                max_tokens,
            )

    # --- Global spend threshold ---
    threshold_setting = session.exec(
        select(AdminSetting).where(AdminSetting.key == _SPEND_THRESHOLD_KEY)
    ).first()

    if threshold_setting:
        try:
            threshold = int(threshold_setting.value)
        except ValueError:
            return

        # Get total tokens this month across all users
        from app.models import UsageRecord

        month_start = datetime.now(timezone.utc).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        total_stmt = select(
            func.coalesce(
                func.sum(UsageRecord.input_tokens + UsageRecord.output_tokens), 0
            )
        ).where(UsageRecord.created_at >= month_start)  # type: ignore[arg-type]
        total_tokens = session.exec(total_stmt).one()

        if total_tokens >= threshold and not _alert_already_sent(
            session, admin.id, AlertType.GLOBAL_SPEND, period
        ):
            _record_alert(session, admin.id, AlertType.GLOBAL_SPEND, period)
            _send_alert_email(
                admin_email,
                "all users",
                AlertType.GLOBAL_SPEND,
                total_tokens,
                threshold,
            )


# --- Alert history ---


def get_alert_history(
    session: Session, skip: int = 0, limit: int = 50
) -> tuple[list[AlertRecordPublic], int]:
    count_stmt = select(func.count()).select_from(AlertRecord)
    count = session.exec(count_stmt).one()

    stmt = (
        select(AlertRecord, User.email)
        .join(User, AlertRecord.user_id == User.id)  # type: ignore[arg-type]
        .order_by(col(AlertRecord.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    rows = session.exec(stmt).all()
    entries = []
    for row in rows:
        record = row[0]  # type: ignore[index]
        email = row[1]  # type: ignore[index]
        entries.append(
            AlertRecordPublic(
                id=record.id,
                user_id=record.user_id,
                user_email=email,
                alert_type=record.alert_type,
                period=record.period,
                created_at=record.created_at,
            )
        )
    return entries, count
