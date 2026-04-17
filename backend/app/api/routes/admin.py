import uuid
from datetime import datetime

import anthropic
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, SessionDep, require_role
from app.core.limiter import limiter
from app.models import (
    ActivityAction,
    ActivityLogResponse,
    AdminSettingsPublic,
    AdminSettingsUpdate,
    ApiKeyStatus,
    RenameHistoryResponse,
    UsageSummary,
    UsageSummaryAdmin,
    UsageTimeseriesPoint,
    UserRole,
)
from app.services.admin import (
    delete_api_key,
    export_activity_csv,
    get_activity_log,
    get_admin_settings,
    get_api_key_status,
    get_usage_summary,
    get_usage_timeseries,
    get_user_recent_activity,
    log_activity,
    parse_range,
    set_api_key,
    update_admin_settings,
)
from app.services.usage import build_usage_summary

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)


# --- Usage summary ---


@router.get("/usage/summary", response_model=UsageSummaryAdmin)
def read_usage_summary(session: SessionDep) -> UsageSummaryAdmin:
    return get_usage_summary(session)


# --- Usage timeseries ---


@router.get("/usage/timeseries", response_model=list[UsageTimeseriesPoint])
def read_usage_timeseries(
    session: SessionDep,
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    time_range: str = Query("30d", pattern="^(\\d+[dy])$", alias="range"),
) -> list[UsageTimeseriesPoint]:
    return get_usage_timeseries(
        session, period=period, range_days=parse_range(time_range)
    )


# --- Per-user timeseries ---


@router.get(
    "/users/{user_id}/usage/timeseries",
    response_model=list[UsageTimeseriesPoint],
)
def read_user_usage_timeseries(
    user_id: uuid.UUID,
    session: SessionDep,
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    time_range: str = Query("30d", pattern="^(\\d+[dy])$", alias="range"),
) -> list[UsageTimeseriesPoint]:
    return get_usage_timeseries(
        session,
        period=period,
        range_days=parse_range(time_range),
        user_id=user_id,
    )


# --- Per-user usage summary (reuses existing service) ---


@router.get("/users/{user_id}/usage/summary", response_model=UsageSummary)
def read_user_usage_summary(user_id: uuid.UUID, session: SessionDep) -> UsageSummary:
    return build_usage_summary(session, user_id)


# --- Per-user recent activity (renames) ---


@router.get("/users/{user_id}/activity", response_model=RenameHistoryResponse)
def read_user_activity(
    user_id: uuid.UUID,
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> RenameHistoryResponse:
    entries, count = get_user_recent_activity(session, user_id, skip, limit)
    return RenameHistoryResponse(data=entries, count=count)


# --- Global activity log ---


@router.get("/activity", response_model=ActivityLogResponse)
def read_activity_log(
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: uuid.UUID | None = None,
    action: ActivityAction | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> ActivityLogResponse:
    entries, count = get_activity_log(
        session,
        skip=skip,
        limit=limit,
        user_id=user_id,
        action=action,
        from_date=from_date,
        to_date=to_date,
    )
    return ActivityLogResponse(data=entries, count=count)


# --- CSV export ---

_MAX_EXPORT_ROWS = 10_000


@router.get("/activity/export")
def export_activity(
    session: SessionDep,
    user_id: uuid.UUID | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> StreamingResponse:
    return StreamingResponse(
        export_activity_csv(
            session,
            user_id=user_id,
            from_date=from_date,
            to_date=to_date,
            max_rows=_MAX_EXPORT_ROWS,
        ),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=activity_log.csv"},
    )


# --- API key management ---


@router.get("/api-key", response_model=ApiKeyStatus)
def read_api_key_status(session: SessionDep) -> ApiKeyStatus:
    return get_api_key_status(session)


class ApiKeySetRequest(BaseModel):
    api_key: str = Field(min_length=1, max_length=500)


@router.put("/api-key", response_model=ApiKeyStatus)
def update_api_key(
    body: ApiKeySetRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> ApiKeyStatus:
    set_api_key(session, body.api_key)
    log_activity(session, current_user.id, ActivityAction.API_KEY_CHANGED)
    return get_api_key_status(session)


@router.delete("/api-key")
def remove_api_key(
    session: SessionDep,
    current_user: CurrentUser,
) -> dict[str, str]:
    delete_api_key(session)
    log_activity(
        session,
        current_user.id,
        ActivityAction.API_KEY_CHANGED,
        detail="API key removed",
    )
    return {"message": "API key removed"}


class ApiKeyValidateResponse(BaseModel):
    valid: bool
    error: str | None = None


@router.post("/api-key/validate", response_model=ApiKeyValidateResponse)
@limiter.limit("10/minute")
def validate_api_key(
    request: Request,  # noqa: ARG001 — required by slowapi rate limiter
    body: ApiKeySetRequest,
) -> ApiKeyValidateResponse:
    try:
        client = anthropic.Anthropic(api_key=body.api_key)
        client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}],
        )
        return ApiKeyValidateResponse(valid=True)
    except anthropic.AuthenticationError:
        return ApiKeyValidateResponse(valid=False, error="Invalid API key")
    except Exception:
        return ApiKeyValidateResponse(valid=False, error="Validation failed")


# --- Admin settings (global defaults) ---


@router.get("/settings", response_model=AdminSettingsPublic)
def read_admin_settings(session: SessionDep) -> AdminSettingsPublic:
    return get_admin_settings(session)


@router.put("/settings", response_model=AdminSettingsPublic)
def update_settings(
    body: AdminSettingsUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> AdminSettingsPublic:
    result = update_admin_settings(
        session,
        default_max_requests_per_day=body.default_max_requests_per_day,
        default_max_tokens_per_month=body.default_max_tokens_per_month,
    )
    log_activity(
        session,
        current_user.id,
        ActivityAction.SETTINGS_CHANGE,
        detail=f"Global defaults updated: {body.model_dump(exclude_none=True)}",
    )
    return result
