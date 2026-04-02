from unittest.mock import MagicMock

from app.services.google_drive import rename_file
from app.services.rename import RenamePreviewItem, _deduplicate_names, execute_rename

# --- Drive rename (mocked) ---


def test_rename_file_calls_drive_api() -> None:
    mock_service = MagicMock()
    mock_service.files().update().execute.return_value = {
        "id": "file1",
        "name": "new_name.pdf",
    }

    result = rename_file(mock_service, "file1", "new_name.pdf")
    assert result["name"] == "new_name.pdf"


# --- Execute rename ---


def test_execute_rename_success() -> None:
    mock_service = MagicMock()
    mock_service.files().update().execute.return_value = {"id": "f1", "name": "new.pdf"}

    results = execute_rename(
        drive_service=mock_service,
        renames=[{"file_id": "f1", "new_name": "new.pdf"}],
    )
    assert len(results) == 1
    assert results[0].success is True


def test_execute_rename_partial_failure() -> None:
    mock_service = MagicMock()

    call_count = 0

    def side_effect(*_args: object, **_kwargs: object) -> dict[str, str]:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            from googleapiclient.errors import HttpError  # type: ignore[import-untyped]

            resp = MagicMock()
            resp.status = 403
            raise HttpError(resp, b"Forbidden")
        return {"id": f"f{call_count}", "name": "renamed.pdf"}

    mock_service.files().update().execute.side_effect = side_effect

    results = execute_rename(
        drive_service=mock_service,
        renames=[
            {"file_id": "f1", "new_name": "a.pdf"},
            {"file_id": "f2", "new_name": "b.pdf"},
            {"file_id": "f3", "new_name": "c.pdf"},
        ],
    )
    assert len(results) == 3
    assert results[0].success is True
    assert results[1].success is False
    assert "permissions" in (results[1].error or "").lower()
    assert results[2].success is True


# --- Deduplicate names ---


def test_deduplicate_no_duplicates() -> None:
    previews = [
        RenamePreviewItem(
            file_id="1", original_name="a.pdf", proposed_name="new_a.pdf"
        ),
        RenamePreviewItem(
            file_id="2", original_name="b.pdf", proposed_name="new_b.pdf"
        ),
    ]
    result = _deduplicate_names(previews)
    assert result[0].proposed_name == "new_a.pdf"
    assert result[1].proposed_name == "new_b.pdf"


def test_deduplicate_with_duplicates() -> None:
    previews = [
        RenamePreviewItem(file_id="1", original_name="a.pdf", proposed_name="same.pdf"),
        RenamePreviewItem(file_id="2", original_name="b.pdf", proposed_name="same.pdf"),
        RenamePreviewItem(file_id="3", original_name="c.pdf", proposed_name="same.pdf"),
    ]
    result = _deduplicate_names(previews)
    assert result[0].proposed_name == "same.pdf"
    assert result[1].proposed_name == "same_1.pdf"
    assert result[2].proposed_name == "same_2.pdf"


def test_deduplicate_preserves_extension() -> None:
    previews = [
        RenamePreviewItem(
            file_id="1", original_name="a.jpeg", proposed_name="photo.jpeg"
        ),
        RenamePreviewItem(
            file_id="2", original_name="b.jpeg", proposed_name="photo.jpeg"
        ),
    ]
    result = _deduplicate_names(previews)
    assert result[0].proposed_name == "photo.jpeg"
    assert result[1].proposed_name == "photo_1.jpeg"


def test_deduplicate_no_extension() -> None:
    previews = [
        RenamePreviewItem(file_id="1", original_name="a", proposed_name="same"),
        RenamePreviewItem(file_id="2", original_name="b", proposed_name="same"),
    ]
    result = _deduplicate_names(previews)
    assert result[0].proposed_name == "same"
    assert result[1].proposed_name == "same_1"
