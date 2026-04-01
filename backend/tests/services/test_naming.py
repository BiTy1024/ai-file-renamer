import pytest

from app.services.naming import (
    apply_convention,
    build_claude_instruction,
    get_file_extension,
    parse_convention,
    sanitize_filename,
    validate_convention,
)

# --- parse_convention ---


def test_parse_simple_convention() -> None:
    fields = parse_convention("[DATE]_[COMPANY]")
    assert fields == ["DATE", "COMPANY"]


def test_parse_complex_convention() -> None:
    fields = parse_convention("[INVOICE_DATE]_[TOTAL]_[COMPANY_NAME]")
    assert fields == ["INVOICE_DATE", "TOTAL", "COMPANY_NAME"]


def test_parse_no_placeholders() -> None:
    fields = parse_convention("just a normal string")
    assert fields == []


def test_parse_with_numbers() -> None:
    fields = parse_convention("[FIELD1]_[FIELD2]")
    assert fields == ["FIELD1", "FIELD2"]


# --- validate_convention ---


def test_validate_valid_convention() -> None:
    fields = validate_convention("[DATE]_[COMPANY]")
    assert len(fields) == 2


def test_validate_no_placeholders_raises() -> None:
    with pytest.raises(ValueError, match="must contain at least one placeholder"):
        validate_convention("no fields here")


def test_validate_unmatched_brackets_raises() -> None:
    with pytest.raises(ValueError, match="unmatched brackets"):
        validate_convention("[DATE_[COMPANY]")


# --- apply_convention ---


def test_apply_basic() -> None:
    result = apply_convention(
        "[DATE]_[COMPANY]",
        {"DATE": "2026-01", "COMPANY": "Acme"},
        ".pdf",
    )
    assert result == "2026-01_Acme.pdf"


def test_apply_preserves_extension() -> None:
    result = apply_convention(
        "[NAME]",
        {"NAME": "report"},
        ".xlsx",
    )
    assert result == "report.xlsx"


def test_apply_missing_field_uses_unknown() -> None:
    result = apply_convention(
        "[DATE]_[MISSING]",
        {"DATE": "2026-01"},
        ".pdf",
    )
    assert result == "2026-01_unknown.pdf"


def test_apply_no_extension() -> None:
    result = apply_convention(
        "[NAME]",
        {"NAME": "readme"},
        "",
    )
    assert result == "readme"


def test_apply_sanitizes_output() -> None:
    result = apply_convention(
        "[DATE]_[COMPANY]",
        {"DATE": "2026/01", "COMPANY": 'Acme: "Corp"'},
        ".pdf",
    )
    assert "/" not in result
    assert ":" not in result
    assert '"' not in result


# --- sanitize_filename ---


def test_sanitize_replaces_invalid_chars() -> None:
    assert sanitize_filename("inv / 2026: test") == "inv _ 2026_ test"


def test_sanitize_collapses_underscores() -> None:
    assert sanitize_filename("a___b") == "a_b"


def test_sanitize_strips_edges() -> None:
    assert sanitize_filename("  _hello_  ") == "hello"


def test_sanitize_preserves_valid() -> None:
    assert sanitize_filename("2026-01-15_Acme_Corp") == "2026-01-15_Acme_Corp"


# --- get_file_extension ---


def test_extension_pdf() -> None:
    assert get_file_extension("invoice.pdf") == ".pdf"


def test_extension_multiple_dots() -> None:
    assert get_file_extension("my.file.name.xlsx") == ".xlsx"


def test_extension_none() -> None:
    assert get_file_extension("noextension") == ""


# --- build_claude_instruction ---


def test_instruction_contains_fields() -> None:
    instruction = build_claude_instruction("[DATE]_[TOTAL]")
    assert "DATE" in instruction
    assert "TOTAL" in instruction
    assert "JSON" in instruction


def test_instruction_with_content_type() -> None:
    instruction = build_claude_instruction("[DATE]", content_type="invoice")
    assert "invoice" in instruction
