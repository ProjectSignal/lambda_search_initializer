import base64
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from config import Config


class RequestValidationError(ValueError):
    """Raised when the incoming request payload is invalid."""


@dataclass
class SearchExecutionRequest:
    search_id: str
    user_id: str
    query: str
    flags: Dict[str, Any]
    initiated_at: str

    def to_stepfunctions_input(self) -> Dict[str, Any]:
        """Convert to Step Functions input format for search pipeline."""
        return {
            "searchId": self.search_id,
            "userId": self.user_id,
            "query": self.query,
            "flags": self.flags,
            "initiatedAt": self.initiated_at,
        }


def parse_event(event: Dict[str, Any], config: Config) -> SearchExecutionRequest:
    """Parse API Gateway event for search pipeline execution."""
    body = _extract_body(event)

    # Extract user ID from API Gateway authorizer context or body
    user_id = None
    if 'requestContext' in event:
        user_id = event.get('requestContext', {}).get('authorizer', {}).get('userId')

    if not user_id:
        user_id = _require_non_empty_string(body, "userId")

    query = _require_non_empty_string(body, "query")
    flags = body.get("flags", {})

    # Set default flags
    default_flags = {
        'hyde_provider': 'groq_llama',
        'description_provider': 'groq_llama',
        'reasoning_model': 'groq_llama',
        'alternative_skills': False,
        'reasoning': False,
        'fallback': False
    }

    # Merge with provided flags
    final_flags = {**default_flags, **flags}

    # Generate unique search ID
    search_id = str(uuid.uuid4())

    # Generate timestamp
    initiated_at = datetime.now(timezone.utc).isoformat()

    return SearchExecutionRequest(
        search_id=search_id,
        user_id=user_id,
        query=query,
        flags=final_flags,
        initiated_at=initiated_at,
    )


def _extract_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and parse request body from API Gateway event."""
    if not isinstance(event, dict):
        raise RequestValidationError("Event payload must be a JSON object")

    if "body" not in event:
        return dict(event)

    body = event.get("body", "")
    if event.get("isBase64Encoded") and isinstance(body, str):
        body = base64.b64decode(body).decode("utf-8")

    if isinstance(body, str):
        body = body.strip()
        if not body:
            return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise RequestValidationError("Request body must be valid JSON") from exc

    if isinstance(body, dict):
        return body

    raise RequestValidationError("Unsupported request body format")


def _require_non_empty_string(payload: Dict[str, Any], field_name: str) -> str:
    """Extract and validate a required non-empty string field."""
    value = payload.get(field_name)
    if value is None:
        raise RequestValidationError(f"{field_name} is required")

    value_str = str(value).strip()
    if not value_str:
        raise RequestValidationError(f"{field_name} cannot be empty")

    return value_str