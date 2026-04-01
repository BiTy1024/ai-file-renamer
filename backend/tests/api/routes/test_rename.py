import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import ServiceAccountCreate, UserCreate, UserRole
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


def _create_user_with_sa(
    db: Session,
    client: TestClient,
    role: UserRole,
) -> dict[str, str]:
    email = random_email()
    password = random_lower_string()
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=password, role=role),
    )
    crud.create_service_account(
        session=db,
        sa_create=ServiceAccountCreate(
            display_name="Test SA",
            credentials_json=VALID_SA_JSON,
            user_id=user.id,
        ),
    )
    r = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# --- Preview tests ---


@patch("app.api.routes.rename.get_drive_service")
@patch("app.api.routes.rename.preview_rename")
def test_preview_returns_proposed_names(
    mock_preview: MagicMock,
    mock_get_service: MagicMock,
    client: TestClient,
    db: Session,
) -> None:
    headers = _create_user_with_sa(db, client, UserRole.USER)
    mock_get_service.return_value = MagicMock()

    from app.services.rename import RenamePreviewItem

    mock_preview.return_value = [
        RenamePreviewItem(
            file_id="file1",
            original_name="scan_001.pdf",
            proposed_name="2026-01-15_Acme.pdf",
        ),
    ]

    r = client.post(
        f"{settings.API_V1_STR}/rename/preview",
        headers=headers,
        json={"folder_id": "folder1", "convention": "[DATE]_[COMPANY]"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["previews"]) == 1
    assert data["previews"][0]["proposed_name"] == "2026-01-15_Acme.pdf"


def test_preview_invalid_convention(client: TestClient, db: Session) -> None:
    headers = _create_user_with_sa(db, client, UserRole.USER)
    r = client.post(
        f"{settings.API_V1_STR}/rename/preview",
        headers=headers,
        json={"folder_id": "folder1", "convention": "no placeholders"},
    )
    assert r.status_code == 422


@patch("app.api.routes.rename.get_drive_service")
@patch("app.api.routes.rename.preview_rename")
def test_viewer_can_call_preview(
    mock_preview: MagicMock,
    mock_get_service: MagicMock,
    client: TestClient,
    db: Session,
) -> None:
    headers = _create_user_with_sa(db, client, UserRole.VIEWER)
    mock_get_service.return_value = MagicMock()
    mock_preview.return_value = []

    r = client.post(
        f"{settings.API_V1_STR}/rename/preview",
        headers=headers,
        json={"folder_id": "folder1", "convention": "[DATE]_[NAME]"},
    )
    assert r.status_code == 200


def test_preview_no_sa(client: TestClient, db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=password, role=UserRole.USER),
    )
    r = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = client.post(
        f"{settings.API_V1_STR}/rename/preview",
        headers=headers,
        json={"folder_id": "folder1", "convention": "[DATE]"},
    )
    assert r.status_code == 404
    assert "No service account" in r.json()["detail"]


# --- Confirm tests ---


@patch("app.api.routes.rename.get_drive_service")
@patch("app.api.routes.rename.execute_rename")
def test_confirm_renames_files(
    mock_execute: MagicMock,
    mock_get_service: MagicMock,
    client: TestClient,
    db: Session,
) -> None:
    headers = _create_user_with_sa(db, client, UserRole.USER)
    mock_get_service.return_value = MagicMock()

    from app.services.rename import RenameResultItem

    mock_execute.return_value = [
        RenameResultItem(file_id="file1", success=True),
        RenameResultItem(file_id="file2", success=True),
    ]

    r = client.post(
        f"{settings.API_V1_STR}/rename/confirm",
        headers=headers,
        json={
            "renames": [
                {"file_id": "file1", "new_name": "new1.pdf"},
                {"file_id": "file2", "new_name": "new2.pdf"},
            ]
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) == 2
    assert all(item["success"] for item in data["results"])


@patch("app.api.routes.rename.get_drive_service")
@patch("app.api.routes.rename.execute_rename")
def test_confirm_partial(
    mock_execute: MagicMock,
    mock_get_service: MagicMock,
    client: TestClient,
    db: Session,
) -> None:
    headers = _create_user_with_sa(db, client, UserRole.USER)
    mock_get_service.return_value = MagicMock()

    from app.services.rename import RenameResultItem

    mock_execute.return_value = [
        RenameResultItem(file_id="file1", success=True),
    ]

    r = client.post(
        f"{settings.API_V1_STR}/rename/confirm",
        headers=headers,
        json={"renames": [{"file_id": "file1", "new_name": "only_this.pdf"}]},
    )
    assert r.status_code == 200
    assert len(r.json()["results"]) == 1


@patch("app.api.routes.rename.get_drive_service")
@patch("app.api.routes.rename.execute_rename")
def test_confirm_with_failure(
    mock_execute: MagicMock,
    mock_get_service: MagicMock,
    client: TestClient,
    db: Session,
) -> None:
    headers = _create_user_with_sa(db, client, UserRole.USER)
    mock_get_service.return_value = MagicMock()

    from app.services.rename import RenameResultItem

    mock_execute.return_value = [
        RenameResultItem(file_id="file1", success=True),
        RenameResultItem(file_id="file2", success=False, error="Permission denied"),
    ]

    r = client.post(
        f"{settings.API_V1_STR}/rename/confirm",
        headers=headers,
        json={
            "renames": [
                {"file_id": "file1", "new_name": "a.pdf"},
                {"file_id": "file2", "new_name": "b.pdf"},
            ]
        },
    )
    assert r.status_code == 200
    results = r.json()["results"]
    assert results[0]["success"] is True
    assert results[1]["success"] is False
    assert results[1]["error"] == "Permission denied"


def test_viewer_cannot_confirm(client: TestClient, db: Session) -> None:
    headers = _create_user_with_sa(db, client, UserRole.VIEWER)

    r = client.post(
        f"{settings.API_V1_STR}/rename/confirm",
        headers=headers,
        json={"renames": [{"file_id": "file1", "new_name": "nope.pdf"}]},
    )
    assert r.status_code == 403
