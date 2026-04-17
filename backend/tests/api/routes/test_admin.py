from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.models import ActivityAction, AdminSetting, UsageRecord, User
from app.services.admin import log_activity


def _login_superuser(client: TestClient) -> dict[str, str]:
    r = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={
            "username": settings.FIRST_SUPERUSER,
            "password": settings.FIRST_SUPERUSER_PASSWORD,
        },
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_superuser(db: Session) -> User:
    from sqlmodel import select

    user = db.exec(select(User).where(User.email == settings.FIRST_SUPERUSER)).first()
    assert user is not None
    return user


# --- Usage summary ---


def test_usage_summary(client: TestClient, db: Session) -> None:
    headers = _login_superuser(client)
    r = client.get(f"{settings.API_V1_STR}/admin/usage/summary", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "current_month_tokens" in data
    assert "previous_month_tokens" in data
    assert "all_time_tokens" in data
    assert "current_month_cost" in data


def test_usage_summary_with_data(client: TestClient, db: Session) -> None:
    user = _get_superuser(db)
    record = UsageRecord(
        user_id=user.id,
        input_tokens=1000,
        output_tokens=500,
        model="claude-sonnet-4-20250514",
    )
    db.add(record)
    db.commit()

    headers = _login_superuser(client)
    r = client.get(f"{settings.API_V1_STR}/admin/usage/summary", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["current_month_tokens"] >= 1500
    assert data["current_month_cost"] > 0

    # Cleanup
    db.delete(record)
    db.commit()


# --- Timeseries ---


def test_usage_timeseries(client: TestClient, db: Session) -> None:
    headers = _login_superuser(client)
    r = client.get(
        f"{settings.API_V1_STR}/admin/usage/timeseries?period=daily&range=30d",
        headers=headers,
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_usage_timeseries_invalid_period(client: TestClient, db: Session) -> None:
    headers = _login_superuser(client)
    r = client.get(
        f"{settings.API_V1_STR}/admin/usage/timeseries?period=hourly",
        headers=headers,
    )
    assert r.status_code == 422


def test_user_usage_timeseries(client: TestClient, db: Session) -> None:
    user = _get_superuser(db)
    headers = _login_superuser(client)
    r = client.get(
        f"{settings.API_V1_STR}/admin/users/{user.id}/usage/timeseries?period=daily&range=30d",
        headers=headers,
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# --- Per-user usage summary ---


def test_user_usage_summary(client: TestClient, db: Session) -> None:
    user = _get_superuser(db)
    headers = _login_superuser(client)
    r = client.get(
        f"{settings.API_V1_STR}/admin/users/{user.id}/usage/summary",
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "requests_today" in data
    assert "tokens_this_month" in data


# --- Activity log ---


def test_activity_log_empty(client: TestClient, db: Session) -> None:
    headers = _login_superuser(client)
    r = client.get(f"{settings.API_V1_STR}/admin/activity", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "count" in data


def test_activity_log_with_entries(client: TestClient, db: Session) -> None:
    user = _get_superuser(db)
    entry = log_activity(db, user.id, ActivityAction.LOGIN, detail="test login")

    headers = _login_superuser(client)
    r = client.get(f"{settings.API_V1_STR}/admin/activity", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    actions = [e["action"] for e in data["data"]]
    assert "login" in actions

    # Cleanup
    db.delete(entry)
    db.commit()


def test_activity_log_filter_by_user(client: TestClient, db: Session) -> None:
    user = _get_superuser(db)
    entry = log_activity(db, user.id, ActivityAction.SETTINGS_CHANGE)

    headers = _login_superuser(client)
    r = client.get(
        f"{settings.API_V1_STR}/admin/activity?user_id={user.id}",
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    for e in data["data"]:
        assert e["user_id"] == str(user.id)

    db.delete(entry)
    db.commit()


def test_activity_log_filter_by_action(client: TestClient, db: Session) -> None:
    user = _get_superuser(db)
    entry = log_activity(db, user.id, ActivityAction.RENAME, tokens_used=100)

    headers = _login_superuser(client)
    r = client.get(
        f"{settings.API_V1_STR}/admin/activity?action=rename",
        headers=headers,
    )
    assert r.status_code == 200
    for e in r.json()["data"]:
        assert e["action"] == "rename"

    db.delete(entry)
    db.commit()


# --- CSV export ---


def test_activity_csv_export(client: TestClient, db: Session) -> None:
    user = _get_superuser(db)
    entry = log_activity(db, user.id, ActivityAction.LOGIN, detail="csv test")

    headers = _login_superuser(client)
    r = client.get(f"{settings.API_V1_STR}/admin/activity/export", headers=headers)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    lines = r.text.strip().splitlines()
    assert lines[0].strip() == "timestamp,user_email,action,detail,tokens_used"
    assert len(lines) >= 2

    db.delete(entry)
    db.commit()


# --- API key management ---


def test_api_key_status_not_set(client: TestClient, db: Session) -> None:
    # Clear any DB key first
    from sqlmodel import delete

    db.exec(delete(AdminSetting).where(AdminSetting.key == "claude_api_key"))
    db.commit()

    headers = _login_superuser(client)
    with patch.object(settings, "CLAUDE_API_KEY", None):
        r = client.get(f"{settings.API_V1_STR}/admin/api-key", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["is_set"] is False
    assert data["source"] == "not_configured"


def test_api_key_set_and_retrieve(client: TestClient, db: Session) -> None:
    headers = _login_superuser(client)

    with patch.object(settings, "CLAUDE_API_KEY", None):
        r = client.put(
            f"{settings.API_V1_STR}/admin/api-key",
            headers=headers,
            json={"api_key": "sk-ant-api03-test-key-1234567890"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["is_set"] is True
        assert data["source"] == "database"
        assert "sk-ant-" in data["masked_key"]
        assert "1234567890" not in data["masked_key"]

        # Verify it's stored encrypted
        from sqlmodel import select

        setting = db.exec(
            select(AdminSetting).where(AdminSetting.key == "claude_api_key")
        ).first()
        assert setting is not None
        assert setting.value != "sk-ant-api03-test-key-1234567890"

    # Cleanup
    db.exec(delete(AdminSetting).where(AdminSetting.key == "claude_api_key"))
    db.commit()


def test_api_key_delete(client: TestClient, db: Session) -> None:
    headers = _login_superuser(client)

    with patch.object(settings, "CLAUDE_API_KEY", None):
        # Set a key first
        client.put(
            f"{settings.API_V1_STR}/admin/api-key",
            headers=headers,
            json={"api_key": "sk-ant-api03-to-delete"},
        )

        # Delete it
        r = client.delete(f"{settings.API_V1_STR}/admin/api-key", headers=headers)
        assert r.status_code == 200

        # Verify it's gone
        r = client.get(f"{settings.API_V1_STR}/admin/api-key", headers=headers)
        assert r.json()["is_set"] is False


def test_api_key_env_takes_precedence(client: TestClient, db: Session) -> None:
    headers = _login_superuser(client)
    with patch.object(settings, "CLAUDE_API_KEY", "sk-ant-api03-from-env-key"):
        r = client.get(f"{settings.API_V1_STR}/admin/api-key", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["is_set"] is True
        assert data["source"] == "env"


def test_api_key_validate_invalid(client: TestClient, db: Session) -> None:
    headers = _login_superuser(client)
    r = client.post(
        f"{settings.API_V1_STR}/admin/api-key/validate",
        headers=headers,
        json={"api_key": "sk-ant-invalid-key"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["valid"] is False


def test_api_key_validate_requires_admin(client: TestClient, db: Session) -> None:
    from app import crud
    from app.models import UserCreate, UserRole
    from tests.utils.utils import random_email, random_lower_string

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
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post(
        f"{settings.API_V1_STR}/admin/api-key/validate",
        headers=headers,
        json={"api_key": "sk-ant-any-key"},
    )
    assert r.status_code == 403


def test_api_key_validate_rate_limit_decorator_applied() -> None:
    from app.api.routes.admin import validate_api_key

    # slowapi wraps the function with functools.wraps, so __wrapped__ points
    # to the original undecorated function when @limiter.limit is applied.
    assert hasattr(validate_api_key, "__wrapped__"), (
        "Rate limit decorator must be applied to validate_api_key"
    )


# --- Admin settings (global defaults) ---


def test_admin_settings_default(client: TestClient, db: Session) -> None:
    headers = _login_superuser(client)
    r = client.get(f"{settings.API_V1_STR}/admin/settings", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "default_max_requests_per_day" in data
    assert "default_max_tokens_per_month" in data


def test_admin_settings_update(client: TestClient, db: Session) -> None:
    headers = _login_superuser(client)
    r = client.put(
        f"{settings.API_V1_STR}/admin/settings",
        headers=headers,
        json={
            "default_max_requests_per_day": 100,
            "default_max_tokens_per_month": 50000,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["default_max_requests_per_day"] == 100
    assert data["default_max_tokens_per_month"] == 50000

    # Verify persistence
    r = client.get(f"{settings.API_V1_STR}/admin/settings", headers=headers)
    data = r.json()
    assert data["default_max_requests_per_day"] == 100

    # Cleanup
    from sqlmodel import delete

    db.exec(delete(AdminSetting))
    db.commit()


# --- Non-admin access ---


def test_non_admin_cannot_access_admin_endpoints(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    endpoints = [
        ("GET", "/admin/usage/summary"),
        ("GET", "/admin/usage/timeseries"),
        ("GET", "/admin/activity"),
        ("GET", "/admin/api-key"),
        ("GET", "/admin/settings"),
    ]
    for method, path in endpoints:
        r = getattr(client, method.lower())(
            f"{settings.API_V1_STR}{path}",
            headers=normal_user_token_headers,
        )
        assert r.status_code == 403, f"{method} {path} should return 403 for non-admin"


# --- Per-user activity ---


def test_user_activity_endpoint(client: TestClient, db: Session) -> None:
    user = _get_superuser(db)
    headers = _login_superuser(client)
    r = client.get(
        f"{settings.API_V1_STR}/admin/users/{user.id}/activity",
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "count" in data
