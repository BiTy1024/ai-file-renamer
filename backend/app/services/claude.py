import json
import logging
from dataclasses import dataclass
from typing import Any

from anthropic import Anthropic, APIError

from app.core.config import settings

logger = logging.getLogger(__name__)


class ClaudeError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass
class ClaudeResponse:
    fields: dict[str, Any]
    input_tokens: int
    output_tokens: int
    model: str


def _get_client() -> Anthropic:
    if not settings.CLAUDE_API_KEY:
        raise ClaudeError(
            "Claude API key not configured. Set CLAUDE_API_KEY in environment.",
            status_code=503,
        )
    return Anthropic(api_key=settings.CLAUDE_API_KEY)


def analyze_file_content(
    *,
    text: str | None = None,
    image_base64: str | None = None,
    mime_type: str | None = None,
    instruction: str,
) -> ClaudeResponse:
    """Send file content to Claude for analysis.

    Supports text content, image content (Vision), or both.
    Returns extracted fields as a dict plus token usage.
    """
    client = _get_client()

    content_blocks: list[dict[str, Any]] = []

    if image_base64 and mime_type:
        content_blocks.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": image_base64,
                },
            }
        )

    if text:
        content_blocks.append({"type": "text", "text": f"File content:\n{text}"})

    if not content_blocks:
        raise ClaudeError("No content provided for analysis", status_code=400)

    content_blocks.append({"type": "text", "text": instruction})

    try:
        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": content_blocks}],  # type: ignore[typeddict-item]
        )
    except APIError as e:
        logger.error("Claude API error: %s", e)
        raise ClaudeError(f"Claude API error: {e.message}", status_code=502)

    first_block = response.content[0] if response.content else None
    response_text = (
        first_block.text if first_block and hasattr(first_block, "text") else ""
    )

    logger.info("Claude raw response: %s", response_text[:500])

    try:
        fields = json.loads(response_text)
    except json.JSONDecodeError:
        logger.warning(
            "Failed to parse Claude response as JSON: %s", response_text[:200]
        )
        fields = {"raw_response": response_text}

    logger.info("Claude extracted fields: %s", fields)

    return ClaudeResponse(
        fields=fields,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        model=settings.CLAUDE_MODEL,
    )
