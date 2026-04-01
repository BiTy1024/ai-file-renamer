import json
import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import UserCreate, UserRole
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


def _create_user_with_role(db: Session, role: UserRole) -> tuple[str, str]:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password, role=role)
    crud.create_user(session=db, user_create=user_in)
    return email, password


def _get_auth_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    r = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- Admin CRUD tests ---


def test_create_service_account(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    email, _ = _create_user_with_role(db, UserRole.USER)
    user = crud.get_user_by_email(session=db, email=email)
    data = {
        "display_name": "Test SA",
        "credentials_json": VALID_SA_JSON,
        "user_id": str(user.id),
    }
    r = client.post(
        f"{settings.API_V1_STR}/service-accounts/",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 200
    sa = r.json()
    assert sa["display_name"] == "Test SA"
    assert sa["user_id"] == str(user.id)
    assert "encrypted_credentials" not in sa


def test_create_service_account_invalid_json(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    email, _ = _create_user_with_role(db, UserRole.USER)
    user = crud.get_user_by_email(session=db, email=email)
    data = {
        "display_name": "Bad SA",
        "credentials_json": "not json",
        "user_id": str(user.id),
    }
    r = client.post(
        f"{settings.API_V1_STR}/service-accounts/",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 422


def test_create_service_account_missing_fields(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    email, _ = _create_user_with_role(db, UserRole.USER)
    user = crud.get_user_by_email(session=db, email=email)
    incomplete_json = json.dumps({"type": "service_account"})
    data = {
        "display_name": "Incomplete SA",
        "credentials_json": incomplete_json,
        "user_id": str(user.id),
    }
    r = client.post(
        f"{settings.API_V1_STR}/service-accounts/",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 422
    assert "Missing required fields" in r.json()["detail"]


def test_create_service_account_duplicate_user(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    email, _ = _create_user_with_role(db, UserRole.USER)
    user = crud.get_user_by_email(session=db, email=email)
    data = {
        "display_name": "SA 1",
        "credentials_json": VALID_SA_JSON,
        "user_id": str(user.id),
    }
    r = client.post(
        f"{settings.API_V1_STR}/service-accounts/",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 200

    data["display_name"] = "SA 2"
    r = client.post(
        f"{settings.API_V1_STR}/service-accounts/",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 400
    assert "already has a service account" in r.json()["detail"]


def test_list_service_accounts(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/service-accounts/",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "count" in data


def test_update_service_account(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    email, _ = _create_user_with_role(db, UserRole.USER)
    user = crud.get_user_by_email(session=db, email=email)
    create_data = {
        "display_name": "Original",
        "credentials_json": VALID_SA_JSON,
        "user_id": str(user.id),
    }
    r = client.post(
        f"{settings.API_V1_STR}/service-accounts/",
        headers=superuser_token_headers,
        json=create_data,
    )
    sa_id = r.json()["id"]

    r = client.patch(
        f"{settings.API_V1_STR}/service-accounts/{sa_id}",
        headers=superuser_token_headers,
        json={"display_name": "Updated"},
    )
    assert r.status_code == 200
    assert r.json()["display_name"] == "Updated"


def test_delete_service_account(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    email, _ = _create_user_with_role(db, UserRole.USER)
    user = crud.get_user_by_email(session=db, email=email)
    create_data = {
        "display_name": "To Delete",
        "credentials_json": VALID_SA_JSON,
        "user_id": str(user.id),
    }
    r = client.post(
        f"{settings.API_V1_STR}/service-accounts/",
        headers=superuser_token_headers,
        json=create_data,
    )
    sa_id = r.json()["id"]

    r = client.delete(
        f"{settings.API_V1_STR}/service-accounts/{sa_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200

    r = client.get(
        f"{settings.API_V1_STR}/service-accounts/{sa_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


# --- Role-based access tests ---


def test_non_admin_cannot_create_service_account(
    client: TestClient, db: Session
) -> None:
    email, password = _create_user_with_role(db, UserRole.USER)
    headers = _get_auth_headers(client, email, password)
    data = {
        "display_name": "Forbidden",
        "credentials_json": VALID_SA_JSON,
        "user_id": str(uuid.uuid4()),
    }
    r = client.post(
        f"{settings.API_V1_STR}/service-accounts/",
        headers=headers,
        json=data,
    )
    assert r.status_code == 403


def test_non_admin_cannot_list_service_accounts(
    client: TestClient, db: Session
) -> None:
    email, password = _create_user_with_role(db, UserRole.VIEWER)
    headers = _get_auth_headers(client, email, password)
    r = client.get(
        f"{settings.API_V1_STR}/service-accounts/",
        headers=headers,
    )
    assert r.status_code == 403


# --- /me endpoint tests ---


def test_read_own_sa_as_user(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    email, password = _create_user_with_role(db, UserRole.USER)
    user = crud.get_user_by_email(session=db, email=email)

    # Admin creates SA for user
    create_data = {
        "display_name": "User SA",
        "credentials_json": VALID_SA_JSON,
        "user_id": str(user.id),
    }
    client.post(
        f"{settings.API_V1_STR}/service-accounts/",
        headers=superuser_token_headers,
        json=create_data,
    )

    # User reads own SA
    headers = _get_auth_headers(client, email, password)
    r = client.get(f"{settings.API_V1_STR}/service-accounts/me", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["display_name"] == "User SA"
    assert data["client_email"] == "test@test-project.iam.gserviceaccount.com"


def test_read_own_sa_as_viewer_hides_email(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    email, password = _create_user_with_role(db, UserRole.VIEWER)
    user = crud.get_user_by_email(session=db, email=email)

    create_data = {
        "display_name": "Viewer SA",
        "credentials_json": VALID_SA_JSON,
        "user_id": str(user.id),
    }
    client.post(
        f"{settings.API_V1_STR}/service-accounts/",
        headers=superuser_token_headers,
        json=create_data,
    )

    headers = _get_auth_headers(client, email, password)
    r = client.get(f"{settings.API_V1_STR}/service-accounts/me", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["display_name"] == "Viewer SA"
    assert data["client_email"] is None


def test_read_own_sa_not_assigned(client: TestClient, db: Session) -> None:
    email, password = _create_user_with_role(db, UserRole.USER)
    headers = _get_auth_headers(client, email, password)
    r = client.get(f"{settings.API_V1_STR}/service-accounts/me", headers=headers)
    assert r.status_code == 404
    assert "No service account assigned" in r.json()["detail"]
