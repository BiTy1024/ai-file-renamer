from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, CurrentUserSA, SessionDep, require_role
from app.models import (
    RenameConfirmRequest,
    RenameConfirmResponse,
    RenameHistoryResponse,
    RenameLog,
    RenamePreview,
    RenamePreviewRequest,
    RenamePreviewResponse,
    RenameResult,
    UserRole,
)
from app.services.google_drive import DriveError, get_drive_service
from app.services.naming import validate_convention
from app.services.rename import execute_rename, preview_rename

router = APIRouter(prefix="/rename", tags=["rename"])


@router.post("/preview", response_model=RenamePreviewResponse)
def rename_preview(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    sa: CurrentUserSA,
    request: RenamePreviewRequest,
) -> Any:
    """Generate rename previews for all files in a folder.

    Any authenticated user can call this (including Viewer for demo purposes).
    """
    try:
        validate_convention(request.convention)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        drive_service = get_drive_service(sa)
    except DriveError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    try:
        items = preview_rename(
            session=session,
            drive_service=drive_service,
            folder_id=request.folder_id,
            convention=request.convention,
            user_id=current_user.id,
            instruction=request.instruction,
            content_type=request.content_type,
        )
    except DriveError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    previews = [
        RenamePreview(
            file_id=item.file_id,
            original_name=item.original_name,
            proposed_name=item.proposed_name,
            error=item.error,
        )
        for item in items
    ]
    return RenamePreviewResponse(previews=previews)


@router.post(
    "/confirm",
    response_model=RenameConfirmResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.USER))],
)
def rename_confirm(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    sa: CurrentUserSA,
    request: RenameConfirmRequest,
) -> Any:
    """Execute file renames on Google Drive.

    Admin and User roles only. Viewer cannot confirm renames.
    Partial confirmation: send only the files you want renamed.
    """
    try:
        drive_service = get_drive_service(sa)
    except DriveError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    renames = [
        {
            "file_id": item.file_id,
            "new_name": item.new_name,
            "original_name": item.original_name,
        }
        for item in request.renames
    ]
    items = execute_rename(
        drive_service=drive_service,
        session=session,
        user_id=current_user.id,
        folder_id=request.folder_id,
        renames=renames,
    )

    results = [
        RenameResult(file_id=item.file_id, success=item.success, error=item.error)
        for item in items
    ]
    return RenameConfirmResponse(results=results)


@router.get("/history", response_model=RenameHistoryResponse)
def read_rename_history(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Get rename history. Admin sees all, others see only their own."""
    if current_user.role == UserRole.ADMIN:
        count_stmt = select(func.count()).select_from(RenameLog)
        query = (
            select(RenameLog)
            .order_by(col(RenameLog.created_at).desc())
            .offset(skip)
            .limit(limit)
        )
    else:
        count_stmt = (
            select(func.count())
            .select_from(RenameLog)
            .where(RenameLog.user_id == current_user.id)
        )
        query = (
            select(RenameLog)
            .where(RenameLog.user_id == current_user.id)
            .order_by(col(RenameLog.created_at).desc())
            .offset(skip)
            .limit(limit)
        )

    count = session.exec(count_stmt).one()
    logs = session.exec(query).all()
    return RenameHistoryResponse(data=logs, count=count)
