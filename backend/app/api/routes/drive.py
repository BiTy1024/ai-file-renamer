from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUserSA
from app.models import (
    DriveFile,
    DriveFileList,
    DriveFolder,
    DriveFolderList,
    DriveFolderSearchResult,
    DriveFolderSearchResultList,
)
from app.services.google_drive import (
    DriveError,
    get_drive_service,
    get_file_metadata,
    list_files,
    list_folders,
    list_subfolders,
    search_folders,
)

router = APIRouter(prefix="/drive", tags=["drive"])


@router.get("/folders", response_model=DriveFolderList)
def read_folders(sa: CurrentUserSA) -> Any:
    """List folders accessible by the current user's service account."""
    try:
        service = get_drive_service(sa)
        raw_folders = list_folders(service)
    except DriveError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    folders = [
        DriveFolder(
            id=f["id"],
            name=f["name"],
            created_time=f.get("createdTime"),
        )
        for f in raw_folders
    ]
    return DriveFolderList(folders=folders)


@router.get("/folders/search", response_model=DriveFolderSearchResultList)
def search_drive_folders(sa: CurrentUserSA, q: str = Query(min_length=1)) -> Any:
    """Search folders by name across all folders accessible by the service account."""
    try:
        service = get_drive_service(sa)
        raw = search_folders(service, q)
    except DriveError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    results = [
        DriveFolderSearchResult(
            id=r["id"],
            name=r["name"],
            parent_name=r.get("parent_name"),
        )
        for r in raw
    ]
    return DriveFolderSearchResultList(results=results)


@router.get("/folders/{folder_id}/subfolders", response_model=DriveFolderList)
def read_folder_subfolders(folder_id: str, sa: CurrentUserSA) -> Any:
    """List subfolders inside a given folder."""
    try:
        service = get_drive_service(sa)
        raw_folders = list_subfolders(service, folder_id)
    except DriveError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    folders = [
        DriveFolder(
            id=f["id"],
            name=f["name"],
            created_time=f.get("createdTime"),
        )
        for f in raw_folders
    ]
    return DriveFolderList(folders=folders)


@router.get("/folders/{folder_id}/files", response_model=DriveFileList)
def read_folder_files(folder_id: str, sa: CurrentUserSA) -> Any:
    """List files in a specific folder (non-recursive)."""
    try:
        service = get_drive_service(sa)
        raw_files = list_files(service, folder_id)
    except DriveError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    files = [
        DriveFile(
            id=f["id"],
            name=f["name"],
            mime_type=f["mimeType"],
            size=f.get("size"),
            modified_time=f.get("modifiedTime"),
            thumbnail_url=f.get("thumbnailLink"),
        )
        for f in raw_files
    ]
    return DriveFileList(files=files)


@router.get("/files/{file_id}", response_model=DriveFile)
def read_file_metadata(file_id: str, sa: CurrentUserSA) -> Any:
    """Get metadata for a specific file."""
    try:
        service = get_drive_service(sa)
        f = get_file_metadata(service, file_id)
    except DriveError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    return DriveFile(
        id=f["id"],
        name=f["name"],
        mime_type=f["mimeType"],
        size=f.get("size"),
        modified_time=f.get("modifiedTime"),
        thumbnail_url=f.get("thumbnailLink"),
    )
