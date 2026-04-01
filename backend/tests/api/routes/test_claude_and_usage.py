import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import UserCreate
from app.services.claude import ClaudeError, analyze_file_content
from app.services.file_extractor import extract_pdf_text
from app.services.usage import (
    RateLimitExceeded,
    check_rate_limit,
    get_user_requests_today,
    get_user_tokens_this_month,
    record_usage,
)
from tests.utils.utils import random_email, random_lower_string

# --- File extraction tests ---


def test_extract_pdf_text_from_bytes() -> None:
    import pymupdf  # type: ignore[import-untyped]

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello World Invoice")
    pdf_bytes = doc.tobytes()
    doc.close()

    text = extract_pdf_text(pdf_bytes)
    assert "Hello World Invoice" in text


# --- Claude service tests (mocked) ---


@patch("app.services.claude._get_client")
def test_analyze_file_content_text(mock_get_client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(text='{"invoice_date": "2026-01-15", "total": "249.00"}')
    ]
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    mock_get_client.return_value = mock_client

    result = analyze_file_content(
        text="Invoice from Acme Corp, date: 2026-01-15, total: 249.00",
        instruction="Extract invoice_date and total as JSON",
    )
    assert result.fields["invoice_date"] == "2026-01-15"
    assert result.fields["total"] == "249.00"
    assert result.input_tokens == 100
    assert result.output_tokens == 50


@patch("app.services.claude._get_client")
def test_analyze_file_content_image(mock_get_client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"company": "Acme"}')]
    mock_response.usage.input_tokens = 200
    mock_response.usage.output_tokens = 30

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    mock_get_client.return_value = mock_client

    result = analyze_file_content(
        image_base64="iVBORw0KGgo...",
        mime_type="image/png",
        instruction="Extract company name",
    )
    assert result.fields["company"] == "Acme"
    assert result.input_tokens == 200


@patch("app.services.claude._get_client")
def test_analyze_no_content_raises(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value = MagicMock()
    try:
        analyze_file_content(instruction="test")
        raise AssertionError("Should have raised")
    except ClaudeError as e:
        assert e.status_code == 400


@patch("app.services.claude.settings")
def test_analyze_missing_api_key(mock_settings: MagicMock) -> None:
    mock_settings.CLAUDE_API_KEY = None
    try:
        analyze_file_content(text="test", instruction="test")
        raise AssertionError("Should have raised")
    except ClaudeError as e:
        assert e.status_code == 503
        assert "not configured" in e.message


# --- Usage tracking tests ---


def test_record_and_query_usage(db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    user = crud.create_user(
        session=db, user_create=UserCreate(email=email, password=password)
    )

    record_usage(
        session=db,
        user_id=user.id,
        input_tokens=100,
        output_tokens=50,
        model="claude-sonnet-4-20250514",
    )

    requests = get_user_requests_today(db, user.id)
    assert requests == 1

    tokens = get_user_tokens_this_month(db, user.id)
    assert tokens == 150


def test_rate_limit_not_exceeded(db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    user = crud.create_user(
        session=db, user_create=UserCreate(email=email, password=password)
    )
    # No limit set → should not raise
    check_rate_limit(db, user.id)


def test_rate_limit_daily_exceeded(db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    user = crud.create_user(
        session=db, user_create=UserCreate(email=email, password=password)
    )

    from app.models import UserLimit

    limit = UserLimit(user_id=user.id, max_requests_per_day=1)
    db.add(limit)
    db.commit()

    record_usage(
        session=db,
        user_id=user.id,
        input_tokens=10,
        output_tokens=5,
        model="test",
    )

    try:
        check_rate_limit(db, user.id)
        raise AssertionError("Should have raised")
    except RateLimitExceeded as e:
        assert "Daily request limit" in e.message


# --- Admin API tests for limits ---


def test_admin_set_user_limits(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    email = random_email()
    password = random_lower_string()
    user = crud.create_user(
        session=db, user_create=UserCreate(email=email, password=password)
    )

    r = client.put(
        f"{settings.API_V1_STR}/users/{user.id}/limits",
        headers=superuser_token_headers,
        json={"max_requests_per_day": 100, "max_tokens_per_month": 50000},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["max_requests_per_day"] == 100
    assert data["max_tokens_per_month"] == 50000


def test_admin_get_user_limits(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    email = random_email()
    password = random_lower_string()
    user = crud.create_user(
        session=db, user_create=UserCreate(email=email, password=password)
    )

    r = client.get(
        f"{settings.API_V1_STR}/users/{user.id}/limits",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["max_requests_per_day"] is None


def test_admin_get_user_usage(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    email = random_email()
    password = random_lower_string()
    user = crud.create_user(
        session=db, user_create=UserCreate(email=email, password=password)
    )

    r = client.get(
        f"{settings.API_V1_STR}/users/{user.id}/usage",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["requests_today"] == 0
    assert data["tokens_this_month"] == 0


def test_non_admin_cannot_set_limits(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    r = client.put(
        f"{settings.API_V1_STR}/users/{uuid.uuid4()}/limits",
        headers=normal_user_token_headers,
        json={"max_requests_per_day": 10},
    )
    assert r.status_code == 403
