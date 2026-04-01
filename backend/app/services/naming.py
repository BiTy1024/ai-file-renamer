import re

PLACEHOLDER_PATTERN = re.compile(r"\[([A-Za-z][A-Za-z0-9_]*)\]")
INVALID_FILENAME_CHARS = re.compile(r'[/\\:*?"<>|]')
MULTI_UNDERSCORE = re.compile(r"_+")


def parse_convention(convention: str) -> list[str]:
    """Extract field names from a naming convention string.

    Example: "[INVOICE_DATE]_[TOTAL]_[COMPANY]" → ["INVOICE_DATE", "TOTAL", "COMPANY"]
    """
    return PLACEHOLDER_PATTERN.findall(convention)


def validate_convention(convention: str) -> list[str]:
    """Validate a naming convention string and return field names.

    Raises ValueError if no placeholders found or syntax is broken.
    """
    fields = parse_convention(convention)
    if not fields:
        raise ValueError(
            "Convention must contain at least one placeholder like [FIELD_NAME]. "
            "Use uppercase letters, numbers, and underscores inside brackets."
        )

    unclosed = convention.count("[") - convention.count("]")
    if unclosed != 0:
        raise ValueError("Convention has unmatched brackets")

    return fields


def build_claude_instruction(
    convention: str,
    content_type: str | None = None,
) -> str:
    """Build a Claude prompt instruction from a naming convention.

    Tells Claude which fields to extract and return as JSON.
    """
    from app.core.config import settings

    fields = parse_convention(convention)
    fields_list = ", ".join(fields)
    language = settings.AI_LANGUAGE

    type_hint = ""
    if content_type:
        type_hint = f"\nThe document is a {content_type}."

    return (
        f"Analyze the provided file content and extract the following fields: {fields_list}.{type_hint}\n"
        f"Return ONLY a JSON object with these exact keys: {fields_list}.\n"
        f"IMPORTANT: All text values MUST be in {language}.\n"
        "Rules:\n"
        '- Use simple values suitable for filenames (no special characters like /\\:*?"<>|)\n'
        "- Replace spaces with underscores\n"
        "- Keep values concise (max 50 chars each)\n"
        "- For DATE fields: use YYYY-MM-DD format. Check file metadata, EXIF data, or content for dates.\n"
        "- For DESCRIPTION fields on images: describe what is visible in the image in detail "
        f"(objects, people, activities, location) — in {language}\n"
        "- If metadata provides a date (e.g. 'Photo taken' or 'File created'), prefer that over 'unknown'\n"
        "- Only use 'unknown' as absolute last resort when no information is available at all.\n"
        "- Always incorporate the user's additional instructions if provided.\n"
        "Example response: {" + ", ".join('"' + f + '": "value"' for f in fields) + "}"
    )


def sanitize_filename(name: str) -> str:
    """Remove or replace characters that are invalid in filenames."""
    name = INVALID_FILENAME_CHARS.sub("_", name)
    name = MULTI_UNDERSCORE.sub("_", name)
    name = name.strip(" _.")
    return name


def apply_convention(
    convention: str,
    fields: dict[str, str],
    original_extension: str,
) -> str:
    """Substitute extracted fields into the convention and add the file extension.

    Example:
        convention = "[DATE]_[COMPANY]"
        fields = {"DATE": "2026-01", "COMPANY": "Acme"}
        original_extension = ".pdf"
        → "2026-01_Acme.pdf"
    """
    result = convention
    fields_lower = {k.lower(): v for k, v in fields.items()}
    for match in PLACEHOLDER_PATTERN.finditer(convention):
        placeholder = match.group(1)
        value = fields_lower.get(placeholder.lower(), "unknown")
        result = result.replace(f"[{placeholder}]", str(value))

    result = PLACEHOLDER_PATTERN.sub("unknown", result)

    result = sanitize_filename(result)

    if original_extension and not result.endswith(original_extension):
        result = f"{result}{original_extension}"

    return result


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename, including the dot."""
    dot_pos = filename.rfind(".")
    if dot_pos == -1:
        return ""
    return filename[dot_pos:]
