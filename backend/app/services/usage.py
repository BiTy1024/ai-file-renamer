import uuid
from datetime import datetime, timezone

from sqlmodel import Session, func, select

from app.models import UsageRecord, UserLimit


class RateLimitExceeded(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def record_usage(
    *,
    session: Session,
    user_id: uuid.UUID,
    input_tokens: int,
    output_tokens: int,
    model: str,
) -> UsageRecord:
    record = UsageRecord(
        user_id=user_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model=model,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def get_user_requests_today(session: Session, user_id: uuid.UUID) -> int:
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    statement = (
        select(func.count())
        .select_from(UsageRecord)
        .where(
            UsageRecord.user_id == user_id,
            UsageRecord.created_at >= today_start,  # type: ignore[operator]
        )
    )
    return session.exec(statement).one()


def get_user_tokens_this_month(session: Session, user_id: uuid.UUID) -> int:
    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    statement = select(
        func.coalesce(func.sum(UsageRecord.input_tokens + UsageRecord.output_tokens), 0)
    ).where(
        UsageRecord.user_id == user_id,
        UsageRecord.created_at >= month_start,  # type: ignore[operator]
    )
    return session.exec(statement).one()


def get_user_limit(session: Session, user_id: uuid.UUID) -> UserLimit | None:
    statement = select(UserLimit).where(UserLimit.user_id == user_id)
    return session.exec(statement).first()


def check_rate_limit(session: Session, user_id: uuid.UUID) -> None:
    """Raises RateLimitExceeded if user has exceeded their limits."""
    limit = get_user_limit(session, user_id)
    if not limit:
        return

    if limit.max_requests_per_day is not None:
        requests_today = get_user_requests_today(session, user_id)
        if requests_today >= limit.max_requests_per_day:
            raise RateLimitExceeded(
                f"Daily request limit reached ({limit.max_requests_per_day} requests/day)"
            )

    if limit.max_tokens_per_month is not None:
        tokens_month = get_user_tokens_this_month(session, user_id)
        if tokens_month >= limit.max_tokens_per_month:
            raise RateLimitExceeded(
                f"Monthly token limit reached ({limit.max_tokens_per_month} tokens/month)"
            )
