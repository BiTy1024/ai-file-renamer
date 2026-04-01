import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, func, select

from app import crud
from app.api.deps import SessionDep, require_role
from app.models import (
    ConventionPreset,
    ConventionPresetCreate,
    ConventionPresetPublic,
    ConventionPresetsPublic,
    ConventionPresetUpdate,
    Message,
    UserRole,
)
from app.services.naming import validate_convention

router = APIRouter(prefix="/presets", tags=["presets"])


@router.get("/", response_model=ConventionPresetsPublic)
def read_presets(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """List all convention presets (any authenticated user)."""
    count_statement = select(func.count()).select_from(ConventionPreset)
    count = session.exec(count_statement).one()
    statement = (
        select(ConventionPreset)
        .order_by(col(ConventionPreset.name))
        .offset(skip)
        .limit(limit)
    )
    presets = session.exec(statement).all()
    return ConventionPresetsPublic(data=presets, count=count)


@router.post(
    "/",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    response_model=ConventionPresetPublic,
)
def create_preset(*, session: SessionDep, preset_in: ConventionPresetCreate) -> Any:
    """Create a convention preset (admin only)."""
    try:
        validate_convention(preset_in.convention)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return crud.create_preset(session=session, preset_in=preset_in)


@router.patch(
    "/{preset_id}",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    response_model=ConventionPresetPublic,
)
def update_preset(
    *, session: SessionDep, preset_id: uuid.UUID, preset_in: ConventionPresetUpdate
) -> Any:
    """Update a convention preset (admin only)."""
    db_preset = session.get(ConventionPreset, preset_id)
    if not db_preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    if preset_in.convention:
        try:
            validate_convention(preset_in.convention)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    return crud.update_preset(session=session, db_preset=db_preset, preset_in=preset_in)


@router.delete("/{preset_id}", dependencies=[Depends(require_role(UserRole.ADMIN))])
def delete_preset(*, session: SessionDep, preset_id: uuid.UUID) -> Message:
    """Delete a convention preset (admin only)."""
    db_preset = session.get(ConventionPreset, preset_id)
    if not db_preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    crud.delete_preset(session=session, db_preset=db_preset)
    return Message(message="Preset deleted successfully")
