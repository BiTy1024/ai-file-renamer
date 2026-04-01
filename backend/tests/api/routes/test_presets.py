from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import UserCreate, UserRole
from tests.utils.utils import random_email, random_lower_string


def _get_user_headers(
    db: Session, client: TestClient, role: UserRole
) -> dict[str, str]:
    email = random_email()
    password = random_lower_string()
    crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=password, role=role),
    )
    r = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_admin_create_preset(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/presets/",
        headers=superuser_token_headers,
        json={
            "name": "Invoice",
            "convention": "[INVOICE_DATE]_[TOTAL]_[COMPANY]",
            "description": "Standard invoice naming",
            "content_type": "invoice",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Invoice"
    assert data["convention"] == "[INVOICE_DATE]_[TOTAL]_[COMPANY]"
    assert data["content_type"] == "invoice"


def test_create_preset_invalid_convention(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/presets/",
        headers=superuser_token_headers,
        json={
            "name": "Bad",
            "convention": "no placeholders here",
        },
    )
    assert r.status_code == 422


def test_list_presets_any_user(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # Create a preset first
    client.post(
        f"{settings.API_V1_STR}/presets/",
        headers=superuser_token_headers,
        json={"name": "Contract", "convention": "[DATE]_[PARTY]"},
    )

    # Viewer can list
    viewer_headers = _get_user_headers(db, client, UserRole.VIEWER)
    r = client.get(f"{settings.API_V1_STR}/presets/", headers=viewer_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1


def test_update_preset(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/presets/",
        headers=superuser_token_headers,
        json={"name": "To Update", "convention": "[DATE]"},
    )
    preset_id = r.json()["id"]

    r = client.patch(
        f"{settings.API_V1_STR}/presets/{preset_id}",
        headers=superuser_token_headers,
        json={"name": "Updated Name"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Updated Name"


def test_delete_preset(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/presets/",
        headers=superuser_token_headers,
        json={"name": "To Delete", "convention": "[NAME]"},
    )
    preset_id = r.json()["id"]

    r = client.delete(
        f"{settings.API_V1_STR}/presets/{preset_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200


def test_non_admin_cannot_create(client: TestClient, db: Session) -> None:
    user_headers = _get_user_headers(db, client, UserRole.USER)
    r = client.post(
        f"{settings.API_V1_STR}/presets/",
        headers=user_headers,
        json={"name": "Nope", "convention": "[DATE]"},
    )
    assert r.status_code == 403


def test_non_admin_cannot_delete(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/presets/",
        headers=superuser_token_headers,
        json={"name": "Protected", "convention": "[DATE]"},
    )
    preset_id = r.json()["id"]

    viewer_headers = _get_user_headers(db, client, UserRole.VIEWER)
    r = client.delete(
        f"{settings.API_V1_STR}/presets/{preset_id}",
        headers=viewer_headers,
    )
    assert r.status_code == 403
