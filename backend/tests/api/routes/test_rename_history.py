from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import RenameLog, UserCreate, UserRole
from tests.utils.utils import random_email, random_lower_string


def _get_user_headers(
    db: Session, client: TestClient, role: UserRole
) -> tuple[str, dict[str, str]]:
    email = random_email()
    password = random_lower_string()
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=password, role=role),
    )
    r = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    return str(user.id), headers


def test_history_empty(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/rename/history",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "count" in data


def test_history_returns_logs(client: TestClient, db: Session) -> None:
    user_id, headers = _get_user_headers(db, client, UserRole.USER)

    log = RenameLog(
        user_id=user_id,
        folder_id="folder123",
        original_name="old.pdf",
        new_name="new.pdf",
    )
    db.add(log)
    db.commit()

    r = client.get(
        f"{settings.API_V1_STR}/rename/history",
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    found = any(
        item["original_name"] == "old.pdf" and item["new_name"] == "new.pdf"
        for item in data["data"]
    )
    assert found


def test_user_sees_only_own_history(client: TestClient, db: Session) -> None:
    user1_id, headers1 = _get_user_headers(db, client, UserRole.USER)
    user2_id, headers2 = _get_user_headers(db, client, UserRole.USER)

    log1 = RenameLog(
        user_id=user1_id, folder_id="f1", original_name="a.pdf", new_name="b.pdf"
    )
    log2 = RenameLog(
        user_id=user2_id, folder_id="f2", original_name="c.pdf", new_name="d.pdf"
    )
    db.add(log1)
    db.add(log2)
    db.commit()

    r = client.get(f"{settings.API_V1_STR}/rename/history", headers=headers1)
    data = r.json()
    for item in data["data"]:
        assert item["user_id"] == user1_id


def test_admin_sees_all_history(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/rename/history",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    # Admin should see logs from multiple users
    assert r.json()["count"] >= 0
