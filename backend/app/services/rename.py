import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlmodel import Session

from app.services.claude import ClaudeError, analyze_file_content
from app.services.file_extractor import (
    download_drive_file,
    extract_content,
    format_metadata_context,
)
from app.services.google_drive import DriveError, list_files, rename_file
from app.services.naming import (
    apply_convention,
    build_claude_instruction,
    get_file_extension,
    validate_convention,
)
from app.services.usage import RateLimitExceeded, check_rate_limit, record_usage

logger = logging.getLogger(__name__)


@dataclass
class RenamePreviewItem:
    file_id: str
    original_name: str
    proposed_name: str
    error: str | None = None


@dataclass
class RenameResultItem:
    file_id: str
    success: bool
    error: str | None = None


def preview_rename(
    *,
    session: Session,
    drive_service: Any,
    folder_id: str,
    convention: str,
    user_id: uuid.UUID,
    instruction: str | None = None,
    content_type: str | None = None,
) -> list[RenamePreviewItem]:
    """Generate rename previews for all files in a folder.

    Downloads each file, extracts content, sends to Claude,
    applies the naming convention.
    """
    validate_convention(convention)
    claude_instruction = build_claude_instruction(convention, content_type)
    if instruction:
        claude_instruction += f"\nAdditional context: {instruction}"

    files = list_files(drive_service, folder_id)
    previews: list[RenamePreviewItem] = []

    for file_info in files:
        file_id = file_info["id"]
        original_name = file_info["name"]
        extension = get_file_extension(original_name)

        try:
            check_rate_limit(session, user_id)
        except RateLimitExceeded as e:
            previews.append(
                RenamePreviewItem(
                    file_id=file_id,
                    original_name=original_name,
                    proposed_name=original_name,
                    error=e.message,
                )
            )
            break

        try:
            logger.info(
                "Processing file %d/%d: %s",
                len(previews) + 1,
                len(files),
                original_name,
            )
            file_bytes, mime_type, drive_metadata = download_drive_file(
                drive_service, file_id
            )
            content = extract_content(file_bytes, mime_type)

            metadata_context = format_metadata_context(drive_metadata)
            full_instruction = claude_instruction
            if metadata_context:
                full_instruction += f"\n\nFile metadata:\n{metadata_context}"

            result = analyze_file_content(
                text=content.get("text"),
                image_base64=content.get("image_base64"),
                mime_type=content.get("mime_type"),
                instruction=full_instruction,
            )

            record_usage(
                session=session,
                user_id=user_id,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                model=result.model,
            )

            proposed = apply_convention(convention, result.fields, extension)
            previews.append(
                RenamePreviewItem(
                    file_id=file_id,
                    original_name=original_name,
                    proposed_name=proposed,
                )
            )
        except (ClaudeError, DriveError) as e:
            logger.warning("Error processing %s: %s", original_name, e)
            previews.append(
                RenamePreviewItem(
                    file_id=file_id,
                    original_name=original_name,
                    proposed_name=original_name,
                    error=str(e),
                )
            )

    return previews


def execute_rename(
    *,
    drive_service: Any,
    session: Session | None = None,
    user_id: uuid.UUID | None = None,
    folder_id: str | None = None,
    renames: list[dict[str, str]],
) -> list[RenameResultItem]:
    """Execute file renames on Google Drive.

    Each item in renames should have 'file_id', 'new_name', and optionally 'original_name'.
    If session/user_id/folder_id provided, logs successful renames.
    """
    from app.models import RenameLog

    results: list[RenameResultItem] = []

    for item in renames:
        file_id = item["file_id"]
        new_name = item["new_name"]
        original_name = item.get("original_name", "")
        try:
            rename_file(drive_service, file_id, new_name)
            results.append(RenameResultItem(file_id=file_id, success=True))

            if session and user_id and folder_id:
                log = RenameLog(
                    user_id=user_id,
                    folder_id=folder_id,
                    original_name=original_name,
                    new_name=new_name,
                )
                session.add(log)
                session.commit()
        except DriveError as e:
            results.append(
                RenameResultItem(file_id=file_id, success=False, error=e.message)
            )

    return results
