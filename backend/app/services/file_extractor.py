import base64
import io
from typing import Any

import pymupdf

GOOGLE_EXPORT_MIME = "application/pdf"
GOOGLE_NATIVE_TYPES = {
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.google-apps.presentation",
}
IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}


def extract_pdf_text(file_bytes: bytes) -> str:
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")  # type: ignore[no-untyped-call]
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())  # type: ignore[no-untyped-call]
    doc.close()  # type: ignore[no-untyped-call]
    return "\n".join(text_parts).strip()


def encode_image_base64(file_bytes: bytes) -> str:
    return base64.standard_b64encode(file_bytes).decode("utf-8")


def download_drive_file(service: Any, file_id: str) -> tuple[bytes, str]:
    """Download a file from Google Drive. Returns (bytes, mime_type)."""
    metadata = (
        service.files()
        .get(fileId=file_id, fields="mimeType", supportsAllDrives=True)
        .execute()
    )
    mime_type: str = metadata["mimeType"]

    if mime_type in GOOGLE_NATIVE_TYPES:
        content = export_google_doc_as_pdf(service, file_id)
        return content, GOOGLE_EXPORT_MIME

    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    from googleapiclient.http import MediaIoBaseDownload  # type: ignore[import-untyped]

    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue(), mime_type


def export_google_doc_as_pdf(service: Any, file_id: str) -> bytes:
    """Export a Google Docs/Sheets/Slides file as PDF."""
    request = service.files().export_media(fileId=file_id, mimeType=GOOGLE_EXPORT_MIME)
    buf = io.BytesIO()
    from googleapiclient.http import MediaIoBaseDownload  # type: ignore[import-untyped]

    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()


def extract_content(file_bytes: bytes, mime_type: str) -> dict[str, str | None]:
    """Extract content from file bytes based on mime type.

    Returns dict with 'text' and/or 'image_base64' and 'mime_type'.
    """
    if mime_type == "application/pdf":
        text = extract_pdf_text(file_bytes)
        return {"text": text, "image_base64": None, "mime_type": mime_type}

    if mime_type in IMAGE_TYPES:
        img_b64 = encode_image_base64(file_bytes)
        return {"text": None, "image_base64": img_b64, "mime_type": mime_type}

    try:
        text = file_bytes.decode("utf-8")
        return {"text": text, "image_base64": None, "mime_type": mime_type}
    except UnicodeDecodeError:
        return {"text": None, "image_base64": None, "mime_type": mime_type}
