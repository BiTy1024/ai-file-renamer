import json
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build  # type: ignore[import-untyped]
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]

from app.core.security import decrypt_text
from app.models import ServiceAccount

SCOPES = ["https://www.googleapis.com/auth/drive"]


class DriveError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def get_drive_service(sa: ServiceAccount) -> Any:
    try:
        creds_json = json.loads(decrypt_text(sa.encrypted_credentials))
    except Exception as e:
        raise DriveError(f"Failed to decrypt credentials: {e}", status_code=400)

    try:
        credentials = Credentials.from_service_account_info(creds_json, scopes=SCOPES)  # type: ignore[no-untyped-call]
        return build("drive", "v3", credentials=credentials)
    except Exception as e:
        raise DriveError(f"Failed to initialize Drive client: {e}", status_code=400)


def list_folders(service: Any) -> list[dict[str, Any]]:
    try:
        results = (
            service.files()
            .list(
                q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="files(id,name,createdTime)",
                orderBy="name",
                pageSize=100,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute()
        )
        folders: list[dict[str, Any]] = results.get("files", [])
        return folders
    except HttpError as e:
        if e.resp.status == 403:
            raise DriveError(
                "Missing permissions to access Google Drive", status_code=403
            )
        raise DriveError(f"Google Drive API error: {e}", status_code=e.resp.status)


def list_subfolders(service: Any, folder_id: str) -> list[dict[str, Any]]:
    try:
        results = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="files(id,name,createdTime)",
                orderBy="name",
                pageSize=100,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute()
        )
        folders: list[dict[str, Any]] = results.get("files", [])
        return folders
    except HttpError as e:
        if e.resp.status == 404:
            raise DriveError("Folder not found", status_code=404)
        if e.resp.status == 403:
            raise DriveError(
                "Missing permissions to access this folder", status_code=403
            )
        raise DriveError(f"Google Drive API error: {e}", status_code=e.resp.status)


def search_folders(service: Any, query: str) -> list[dict[str, Any]]:
    """Search folders by name. Returns results with immediate parent name for path display."""
    try:
        # Escape single quotes in query to prevent injection into Drive query syntax
        safe_query = query.replace("'", "\\'")
        results = (
            service.files()
            .list(
                q=f"name contains '{safe_query}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="files(id,name,parents)",
                orderBy="name",
                pageSize=50,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute()
        )
        folders: list[dict[str, Any]] = results.get("files", [])
    except HttpError as e:
        if e.resp.status == 403:
            raise DriveError(
                "Missing permissions to access Google Drive", status_code=403
            )
        raise DriveError(f"Google Drive API error: {e}", status_code=e.resp.status)

    if not folders:
        return []

    # Collect unique parent IDs to resolve parent names in one batch call
    parent_ids: set[str] = set()
    for folder in folders:
        if folder.get("parents"):
            parent_ids.add(folder["parents"][0])

    parent_names: dict[str, str] = {}
    if parent_ids:
        id_filter = " or ".join(f"id='{pid}'" for pid in parent_ids)
        try:
            parent_results = (
                service.files()
                .list(
                    q=f"({id_filter}) and trashed=false",
                    fields="files(id,name)",
                    pageSize=len(parent_ids),
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True,
                )
                .execute()
            )
            for p in parent_results.get("files", []):
                parent_names[p["id"]] = p["name"]
        except HttpError:
            pass  # Parent names are best-effort; missing them is non-fatal

    enriched: list[dict[str, Any]] = []
    for folder in folders:
        parent_id = folder["parents"][0] if folder.get("parents") else None
        enriched.append(
            {
                "id": folder["id"],
                "name": folder["name"],
                "parent_name": parent_names.get(parent_id) if parent_id else None,
            }
        )
    return enriched


def list_files(service: Any, folder_id: str) -> list[dict[str, Any]]:
    try:
        results = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and mimeType!='application/vnd.google-apps.folder' and trashed=false",
                fields="files(id,name,mimeType,size,modifiedTime,thumbnailLink)",
                orderBy="name",
                pageSize=200,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute()
        )
        files: list[dict[str, Any]] = results.get("files", [])
        return files
    except HttpError as e:
        if e.resp.status == 404:
            raise DriveError("Folder not found", status_code=404)
        if e.resp.status == 403:
            raise DriveError(
                "Missing permissions to access this folder", status_code=403
            )
        raise DriveError(f"Google Drive API error: {e}", status_code=e.resp.status)


def get_file_metadata(service: Any, file_id: str) -> dict[str, Any]:
    try:
        result: dict[str, Any] = (
            service.files()
            .get(
                fileId=file_id,
                fields="id,name,mimeType,size,modifiedTime,thumbnailLink",
                supportsAllDrives=True,
            )
            .execute()
        )
        return result
    except HttpError as e:
        if e.resp.status == 404:
            raise DriveError("File not found", status_code=404)
        if e.resp.status == 403:
            raise DriveError("Missing permissions to access this file", status_code=403)
        raise DriveError(f"Google Drive API error: {e}", status_code=e.resp.status)


def rename_file(service: Any, file_id: str, new_name: str) -> dict[str, Any]:
    """Rename a file on Google Drive."""
    try:
        result: dict[str, Any] = (
            service.files()
            .update(
                fileId=file_id,
                body={"name": new_name},
                fields="id,name",
                supportsAllDrives=True,
            )
            .execute()
        )
        return result
    except HttpError as e:
        if e.resp.status == 404:
            raise DriveError("File not found", status_code=404)
        if e.resp.status == 403:
            raise DriveError("Missing permissions to rename this file", status_code=403)
        raise DriveError(f"Google Drive API error: {e}", status_code=e.resp.status)
