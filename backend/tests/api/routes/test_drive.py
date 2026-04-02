import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import UserCreate, UserRole
from app.services.google_drive import DriveError
from tests.utils.utils import random_email, random_lower_string

VALID_SA_JSON = json.dumps(
    {
        "type": "service_account",
        "project_id": "test-project",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----\n",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
    }
)

MOCK_FOLDERS = [
    {"id": "folder1", "name": "Invoices", "createdTime": "2026-01-01T00:00:00Z"},
    {"id": "folder2", "name": "Contracts", "createdTime": "2026-02-01T00:00:00Z"},
]

MOCK_FILES = [
    {
        "id": "file1",
        "name": "invoice_001.pdf",
        "mimeType": "application/pdf",
        "size": "12345",
        "modifiedTime": "2026-03-01T00:00:00Z",
        "thumbnailLink": "https://example.com/thumb1",
    },
    {
        "id": "file2",
        "name": "invoice_002.pdf",
        "mimeType": "application/pdf",
        "size": "67890",
        "modifiedTime": "2026-03-15T00:00:00Z",
        "thumbnailLink": None,
    },
]

MOCK_FILE_METADATA = {
    "id": "file1",
    "name": "invoice_001.pdf",
    "mimeType": "application/pdf",
    "size": "12345",
    "modifiedTime": "2026-03-01T00:00:00Z",
    "thumbnailLink": "https://example.com/thumb1",
}


def _create_user_with_sa(
    db: Session, client: TestClient, admin_headers: dict[str, str], role: UserRole
) -> tuple[str, str, dict[str, str]]:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password, role=role)
    user = crud.create_user(session=db, user_create=user_in)

    client.post(
        f"{settings.API_V1_STR}/service-accounts/",
        headers=admin_headers,
        json={
            "display_name": "Test SA",
            "credentials_json": VALID_SA_JSON,
            "user_id": str(user.id),
        },
    )

    r = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    return email, password, headers


# --- List folders ---


@patch("app.api.routes.drive.get_drive_service")
@patch("app.api.routes.drive.list_folders")
def test_list_folders(
    mock_list_folders: MagicMock,
    mock_get_service: MagicMock,
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    _, _, headers = _create_user_with_sa(
        db, client, superuser_token_headers, UserRole.USER
    )
    mock_get_service.return_value = MagicMock()
    mock_list_folders.return_value = MOCK_FOLDERS

    r = client.get(f"{settings.API_V1_STR}/drive/folders", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["folders"]) == 2
    assert data["folders"][0]["name"] == "Invoices"
    assert data["folders"][1]["name"] == "Contracts"


# --- List files ---


@patch("app.api.routes.drive.get_drive_service")
@patch("app.api.routes.drive.list_files")
def test_list_files_in_folder(
    mock_list_files: MagicMock,
    mock_get_service: MagicMock,
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    _, _, headers = _create_user_with_sa(
        db, client, superuser_token_headers, UserRole.USER
    )
    mock_get_service.return_value = MagicMock()
    mock_list_files.return_value = MOCK_FILES

    r = client.get(
        f"{settings.API_V1_STR}/drive/folders/folder1/files", headers=headers
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["files"]) == 2
    assert data["files"][0]["name"] == "invoice_001.pdf"
    assert data["files"][0]["mime_type"] == "application/pdf"
    assert data["files"][0]["size"] == "12345"


# --- File metadata ---


@patch("app.api.routes.drive.get_drive_service")
@patch("app.api.routes.drive.get_file_metadata")
def test_get_file_metadata(
    mock_get_metadata: MagicMock,
    mock_get_service: MagicMock,
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    _, _, headers = _create_user_with_sa(
        db, client, superuser_token_headers, UserRole.USER
    )
    mock_get_service.return_value = MagicMock()
    mock_get_metadata.return_value = MOCK_FILE_METADATA

    r = client.get(f"{settings.API_V1_STR}/drive/files/file1", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "file1"
    assert data["name"] == "invoice_001.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["thumbnail_url"] == "https://example.com/thumb1"


# --- Error cases ---


def test_no_sa_assigned(client: TestClient, db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password, role=UserRole.USER)
    crud.create_user(session=db, user_create=user_in)

    r = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = client.get(f"{settings.API_V1_STR}/drive/folders", headers=headers)
    assert r.status_code == 404
    assert "No service account assigned" in r.json()["detail"]


@patch("app.api.routes.drive.get_drive_service")
@patch("app.api.routes.drive.list_folders")
def test_drive_permission_error(
    mock_list_folders: MagicMock,
    mock_get_service: MagicMock,
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    _, _, headers = _create_user_with_sa(
        db, client, superuser_token_headers, UserRole.USER
    )
    mock_get_service.return_value = MagicMock()
    mock_list_folders.side_effect = DriveError(
        "Missing permissions to access Google Drive", status_code=403
    )

    r = client.get(f"{settings.API_V1_STR}/drive/folders", headers=headers)
    assert r.status_code == 403
    assert "Missing permissions" in r.json()["detail"]


@patch("app.api.routes.drive.get_drive_service")
@patch("app.api.routes.drive.list_files")
def test_drive_folder_not_found(
    mock_list_files: MagicMock,
    mock_get_service: MagicMock,
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    _, _, headers = _create_user_with_sa(
        db, client, superuser_token_headers, UserRole.USER
    )
    mock_get_service.return_value = MagicMock()
    mock_list_files.side_effect = DriveError("Folder not found", status_code=404)

    r = client.get(
        f"{settings.API_V1_STR}/drive/folders/nonexistent/files", headers=headers
    )
    assert r.status_code == 404
    assert "Folder not found" in r.json()["detail"]


# --- Viewer can also access drive ---


@patch("app.api.routes.drive.get_drive_service")
@patch("app.api.routes.drive.list_folders")
def test_viewer_can_list_folders(
    mock_list_folders: MagicMock,
    mock_get_service: MagicMock,
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    _, _, headers = _create_user_with_sa(
        db, client, superuser_token_headers, UserRole.VIEWER
    )
    mock_get_service.return_value = MagicMock()
    mock_list_folders.return_value = MOCK_FOLDERS

    r = client.get(f"{settings.API_V1_STR}/drive/folders", headers=headers)
    assert r.status_code == 200
    assert len(r.json()["folders"]) == 2


# --- Subfolders ---


MOCK_SUBFOLDERS = [
    {"id": "sf1", "name": "Sub A", "createdTime": "2026-01-01T00:00:00Z"},
    {"id": "sf2", "name": "Sub B", "createdTime": "2026-02-01T00:00:00Z"},
]

MOCK_SEARCH_RESULTS = [
    {"id": "f1", "name": "Invoices", "parent_name": "Root"},
    {"id": "f2", "name": "Invoices 2024", "parent_name": None},
]


@patch("app.api.routes.drive.get_drive_service")
@patch("app.api.routes.drive.list_subfolders")
def test_list_subfolders_returns_list(
    mock_list_subfolders: MagicMock,
    mock_get_service: MagicMock,
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    _, _, headers = _create_user_with_sa(
        db, client, superuser_token_headers, UserRole.USER
    )
    mock_get_service.return_value = MagicMock()
    mock_list_subfolders.return_value = MOCK_SUBFOLDERS

    r = client.get(
        f"{settings.API_V1_STR}/drive/folders/folder1/subfolders", headers=headers
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["folders"]) == 2
    assert data["folders"][0]["id"] == "sf1"
    assert data["folders"][0]["name"] == "Sub A"


@patch("app.api.routes.drive.get_drive_service")
@patch("app.api.routes.drive.list_subfolders")
def test_list_subfolders_returns_empty_list(
    mock_list_subfolders: MagicMock,
    mock_get_service: MagicMock,
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    _, _, headers = _create_user_with_sa(
        db, client, superuser_token_headers, UserRole.USER
    )
    mock_get_service.return_value = MagicMock()
    mock_list_subfolders.return_value = []

    r = client.get(
        f"{settings.API_V1_STR}/drive/folders/folder1/subfolders", headers=headers
    )
    assert r.status_code == 200
    assert r.json()["folders"] == []


def test_list_subfolders_no_sa_returns_404(
    client: TestClient,
    db: Session,
) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password, role=UserRole.USER)
    crud.create_user(session=db, user_create=user_in)
    r = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = client.get(
        f"{settings.API_V1_STR}/drive/folders/folder1/subfolders", headers=headers
    )
    assert r.status_code == 404


@patch("app.api.routes.drive.get_drive_service")
@patch("app.api.routes.drive.list_subfolders")
def test_list_subfolders_drive_error_propagates(
    mock_list_subfolders: MagicMock,
    mock_get_service: MagicMock,
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    _, _, headers = _create_user_with_sa(
        db, client, superuser_token_headers, UserRole.USER
    )
    mock_get_service.return_value = MagicMock()
    mock_list_subfolders.side_effect = DriveError("Folder not found", status_code=404)

    r = client.get(
        f"{settings.API_V1_STR}/drive/folders/nonexistent/subfolders", headers=headers
    )
    assert r.status_code == 404
    assert "Folder not found" in r.json()["detail"]


# --- Search ---


@patch("app.api.routes.drive.get_drive_service")
@patch("app.api.routes.drive.search_folders")
def test_search_folders_returns_results(
    mock_search: MagicMock,
    mock_get_service: MagicMock,
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    _, _, headers = _create_user_with_sa(
        db, client, superuser_token_headers, UserRole.USER
    )
    mock_get_service.return_value = MagicMock()
    mock_search.return_value = MOCK_SEARCH_RESULTS

    r = client.get(f"{settings.API_V1_STR}/drive/folders/search?q=inv", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) == 2
    assert data["results"][0]["name"] == "Invoices"
    assert data["results"][0]["parent_name"] == "Root"
    assert data["results"][1]["parent_name"] is None


@patch("app.api.routes.drive.get_drive_service")
@patch("app.api.routes.drive.search_folders")
def test_search_folders_returns_empty_list(
    mock_search: MagicMock,
    mock_get_service: MagicMock,
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    _, _, headers = _create_user_with_sa(
        db, client, superuser_token_headers, UserRole.USER
    )
    mock_get_service.return_value = MagicMock()
    mock_search.return_value = []

    r = client.get(f"{settings.API_V1_STR}/drive/folders/search?q=xyz", headers=headers)
    assert r.status_code == 200
    assert r.json()["results"] == []


def test_search_folders_missing_query_returns_422(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    _, _, headers = _create_user_with_sa(
        db, client, superuser_token_headers, UserRole.USER
    )
    r = client.get(f"{settings.API_V1_STR}/drive/folders/search", headers=headers)
    assert r.status_code == 422


def test_search_folders_no_sa_returns_404(
    client: TestClient,
    db: Session,
) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password, role=UserRole.USER)
    crud.create_user(session=db, user_create=user_in)
    r = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = client.get(
        f"{settings.API_V1_STR}/drive/folders/search?q=test", headers=headers
    )
    assert r.status_code == 404
