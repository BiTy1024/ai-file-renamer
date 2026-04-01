"""Integration tests for Google Drive API.

These tests call the real Google Drive API using a service account.
They require:
- GOOGLE_SA_CREDENTIALS_JSON env var (the full SA JSON string)
- GOOGLE_TEST_FOLDER_ID env var (ID of a folder shared with the SA)

Skip automatically if credentials are not provided.
Run locally: set env vars and run `pytest tests/integration/ -v`
Run in CI: provided via GitHub Secrets.
"""

import json
import os
from pathlib import Path

import pytest
from dotenv import dotenv_values

from app.core.security import encrypt_text
from app.models import ServiceAccount
from app.services.google_drive import (
    get_drive_service,
    get_file_metadata,
    list_files,
    list_folders,
)

# Load from .env file directly (preserves JSON quotes that shell sourcing breaks)
_env_file = Path(__file__).resolve().parents[3] / ".env"
_env_values = dotenv_values(_env_file) if _env_file.exists() else {}

SA_JSON = os.environ.get("GOOGLE_SA_CREDENTIALS_JSON") or _env_values.get(
    "GOOGLE_SA_CREDENTIALS_JSON"
)
TEST_FOLDER_ID = os.environ.get("GOOGLE_TEST_FOLDER_ID") or _env_values.get(
    "GOOGLE_TEST_FOLDER_ID"
)

skip_no_credentials = pytest.mark.skipif(
    not SA_JSON, reason="GOOGLE_SA_CREDENTIALS_JSON not set"
)
skip_no_folder = pytest.mark.skipif(
    not TEST_FOLDER_ID, reason="GOOGLE_TEST_FOLDER_ID not set"
)


def _make_sa() -> ServiceAccount:
    """Build a ServiceAccount object with encrypted credentials for testing."""
    encrypted = encrypt_text(SA_JSON)  # type: ignore[arg-type]
    sa = ServiceAccount(
        display_name="Integration Test SA",
        encrypted_credentials=encrypted,
        user_id="00000000-0000-0000-0000-000000000000",  # type: ignore[arg-type]
    )
    return sa


@skip_no_credentials
def test_get_drive_service_succeeds() -> None:
    sa = _make_sa()
    service = get_drive_service(sa)
    assert service is not None


@skip_no_credentials
def test_list_folders_returns_list() -> None:
    sa = _make_sa()
    service = get_drive_service(sa)
    folders = list_folders(service)
    assert isinstance(folders, list)
    # At least one folder should be shared with the SA
    assert len(folders) > 0, "No folders found — is a folder shared with the SA?"
    assert "id" in folders[0]
    assert "name" in folders[0]


@skip_no_credentials
@skip_no_folder
def test_list_files_in_folder() -> None:
    sa = _make_sa()
    service = get_drive_service(sa)
    files = list_files(service, TEST_FOLDER_ID)  # type: ignore[arg-type]
    assert isinstance(files, list)
    if files:
        assert "id" in files[0]
        assert "name" in files[0]
        assert "mimeType" in files[0]


@skip_no_credentials
@skip_no_folder
def test_list_files_includes_shared_files() -> None:
    """Verify that shared files show up (the bug we caught)."""
    sa = _make_sa()
    service = get_drive_service(sa)
    files = list_files(service, TEST_FOLDER_ID)  # type: ignore[arg-type]
    assert isinstance(files, list)
    assert len(files) > 0, "No files found in test folder — add at least one file"


@skip_no_credentials
@skip_no_folder
def test_get_file_metadata_returns_fields() -> None:
    sa = _make_sa()
    service = get_drive_service(sa)
    files = list_files(service, TEST_FOLDER_ID)  # type: ignore[arg-type]
    assert len(files) > 0, "Need at least one file in the test folder"

    metadata = get_file_metadata(service, files[0]["id"])
    assert metadata["id"] == files[0]["id"]
    assert "name" in metadata
    assert "mimeType" in metadata
