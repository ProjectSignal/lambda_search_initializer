import json
import os
from typing import Any, Dict, Optional, Tuple

from config import Config, ConfigurationError
from logging_config import get_logger
from request_parser import RequestValidationError, parse_event
from stepfunctions_client import StepFunctionsExecutor, WorkflowStartError

logger = get_logger(__name__)

_config: Optional[Config] = None
_executor: Optional[StepFunctionsExecutor] = None

def lambda_handler(event: Optional[Dict[str, Any]], context: Any) -> Dict[str, Any]:
    """AWS Lambda entrypoint triggered by API Gateway."""
    if _is_options_request(event):
        return _build_response(204, {})

    try:
        config, executor = _get_runtime_dependencies()
        execution_request = parse_event(event or {}, config)

        trace_header = _extract_trace_header(event)
        response = executor.start_execution(execution_request, trace_header=trace_header)

        start_date = response.get("startDate")
        if hasattr(start_date, "isoformat"):
            start_date = start_date.isoformat()

        logger.info(
            "Started search pipeline execution %s for search %s user %s",
            response.get("executionName"),
            execution_request.search_id,
            execution_request.user_id,
        )

        body = {
            "success": True,
            "executionArn": response.get("executionArn"),
            "executionName": response.get("executionName"),
            "startDate": start_date,
            "searchId": execution_request.search_id,
            "userId": execution_request.user_id,
            "query": execution_request.query,
            "flags": execution_request.flags,
            "pipeline": "search"
        }
        return _build_response(200, body)

    except RequestValidationError as exc:
        logger.warning("Request validation failed: %s", exc)
        return _build_response(400, {"success": False, "error": str(exc)})
    except ConfigurationError as exc:
        logger.error("Configuration error detected: %s", exc)
        return _build_response(500, {"success": False, "error": "Server configuration error"})
    except WorkflowStartError as exc:
        logger.error("Failed to start Step Functions execution: %s", exc)
        return _build_response(502, {"success": False, "error": "Failed to start workflow"})
    except Exception:  # pragma: no cover
        logger.exception("Unhandled exception while starting workflow")
        return _build_response(500, {"success": False, "error": "Internal server error"})


def _get_runtime_dependencies() -> Tuple[Config, StepFunctionsExecutor]:
    global _config, _executor

    if _config is None:
        _config = Config.load()
        logger.debug("Configuration loaded for state machine %s", _config.state_machine_arn)
    if _executor is None:
        _executor = StepFunctionsExecutor(_config)
        logger.debug("Step Functions client initialised")

    return _config, _executor


def _extract_trace_header(event: Optional[Dict[str, Any]]) -> Optional[str]:
    if not event or not isinstance(event, dict):
        return None
    headers = event.get("headers")
    if not isinstance(headers, dict):
        return None

    return headers.get("X-Amzn-Trace-Id") or headers.get("x-amzn-trace-id")


def _is_options_request(event: Optional[Dict[str, Any]]) -> bool:
    if not event or not isinstance(event, dict):
        return False
    method = event.get("httpMethod") or event.get("requestContext", {}).get("httpMethod")
    return isinstance(method, str) and method.upper() == "OPTIONS"


def _build_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    cors_origin = _get_cors_origin()
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": cors_origin,
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Requested-With",
        "Access-Control-Allow-Methods": "OPTIONS,POST",
    }

    if status_code == 204:
        return {
            "statusCode": status_code,
            "headers": headers,
            "body": "",
        }

    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body),
    }


def _get_cors_origin() -> str:
    if _config is not None:
        return _config.cors_allowed_origin or "*"
    return os.getenv("CORS_ALLOWED_ORIGIN", "*")

