"""JSON extraction helpers for LLM responses."""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class JSONExtractionError(Exception):
    """Raised when JSON cannot be extracted from response."""
    pass


def extract_json_from_response(content: str | None) -> dict[str, Any]:
    """
    Extract JSON from LLM response that may contain markdown code blocks.
    
    LLMs often wrap JSON in ```json ... ``` blocks even when asked not to.
    This function handles various response formats.
    
    Args:
        content: Raw response content from LLM
        
    Returns:
        Parsed JSON as dictionary
        
    Raises:
        JSONExtractionError: If content is empty or cannot be parsed
    """
    if not content:
        raise JSONExtractionError("Empty response content")
    
    json_content = content.strip()
    
    # Try to extract from markdown code blocks
    if "```json" in content:
        try:
            json_content = content.split("```json")[1].split("```")[0].strip()
        except IndexError:
            logger.warning("Found ```json but couldn't extract content")
    elif "```" in content:
        try:
            parts = content.split("```")
            if len(parts) >= 2:
                # Take the first code block
                json_content = parts[1].strip()
                # If it starts with a language identifier, skip the first line
                if json_content and not json_content.startswith('{'):
                    lines = json_content.split('\n')
                    if len(lines) > 1:
                        json_content = '\n'.join(lines[1:]).strip()
        except (IndexError, ValueError):
            logger.warning("Found ``` but couldn't extract content")
    
    # Try to find JSON object boundaries if not a clean JSON
    if not json_content.startswith('{'):
        start_idx = json_content.find('{')
        if start_idx != -1:
            # Find matching closing brace
            brace_count = 0
            for i, char in enumerate(json_content[start_idx:], start_idx):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_content = json_content[start_idx:i+1]
                        break
    
    try:
        return json.loads(json_content)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.debug(f"Content that failed to parse: {json_content[:500]}")
        raise JSONExtractionError(f"Failed to parse JSON: {e}") from e
