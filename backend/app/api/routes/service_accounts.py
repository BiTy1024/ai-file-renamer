import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, func, select

from app import crud
from app.api.deps import CurrentUser, SessionDep, require_role
from app.models import (
    Message,
    ServiceAccount,
    ServiceAccountCreate,
    ServiceAccountPublic,
    ServiceAccountPublicWithEmail,
    ServiceAccountsPublic,
    ServiceAccountUpdate,
    UserRole,
)

router = APIRouter(prefix="/service-accounts", tags=["service-accounts"])


@router.get(
    "/",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    response_model=ServiceAccountsPublic,
)
def read_service_accounts(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """List all service accounts (admin only)."""
    count_statement = select(func.count()).select_from(ServiceAccount)
    count = session.exec(count_statement).one()
    statement = (
        select(ServiceAccount)
        .order_by(col(ServiceAccount.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    items = session.exec(statement).all()
    return ServiceAccountsPublic(data=items, count=count)


@router.post(
    "/",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    response_model=ServiceAccountPublic,
)
def create_service_account(*, session: SessionDep, sa_in: ServiceAccountCreate) -> Any:
    """Create a service account and assign to a user (admin only)."""
    existing = crud.get_service_account_by_user_id(
        session=session, user_id=sa_in.user_id
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="This user already has a service account assigned"
        )
    from app.models import User

    user = session.get(User, sa_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        sa = crud.create_service_account(session=session, sa_create=sa_in)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return sa


@router.get("/me", response_model=ServiceAccountPublicWithEmail)
def read_own_service_account(session: SessionDep, current_user: CurrentUser) -> Any:
    """Get the service account assigned to the current user."""
    sa = crud.get_service_account_by_user_id(session=session, user_id=current_user.id)
    if not sa:
        raise HTTPException(
            status_code=404, detail="No service account assigned to your account"
        )
    client_email = None
    if current_user.role in (UserRole.ADMIN, UserRole.USER):
        client_email = crud.get_service_account_client_email(sa)
    return ServiceAccountPublicWithEmail(
        id=sa.id,
        display_name=sa.display_name,
        description=sa.description,
        user_id=sa.user_id,
        created_at=sa.created_at,
        client_email=client_email,
    )


@router.get(
    "/{sa_id}",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    response_model=ServiceAccountPublic,
)
def read_service_account(*, session: SessionDep, sa_id: uuid.UUID) -> Any:
    """Get a specific service account by ID (admin only)."""
    sa = session.get(ServiceAccount, sa_id)
    if not sa:
        raise HTTPException(status_code=404, detail="Service account not found")
    return sa


@router.patch(
    "/{sa_id}",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    response_model=ServiceAccountPublic,
)
def update_service_account(
    *, session: SessionDep, sa_id: uuid.UUID, sa_in: ServiceAccountUpdate
) -> Any:
    """Update a service account (admin only)."""
    db_sa = session.get(ServiceAccount, sa_id)
    if not db_sa:
        raise HTTPException(status_code=404, detail="Service account not found")
    if sa_in.user_id and sa_in.user_id != db_sa.user_id:
        existing = crud.get_service_account_by_user_id(
            session=session, user_id=sa_in.user_id
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Target user already has a service account assigned",
            )
    try:
        return crud.update_service_account(session=session, db_sa=db_sa, sa_in=sa_in)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/{sa_id}", dependencies=[Depends(require_role(UserRole.ADMIN))])
def delete_service_account(*, session: SessionDep, sa_id: uuid.UUID) -> Message:
    """Delete a service account (admin only)."""
    db_sa = session.get(ServiceAccount, sa_id)
    if not db_sa:
        raise HTTPException(status_code=404, detail="Service account not found")
    crud.delete_service_account(session=session, db_sa=db_sa)
    return Message(message="Service account deleted successfully")
