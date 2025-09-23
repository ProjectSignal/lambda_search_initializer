import json
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from config import Config
from request_parser import SearchExecutionRequest
from utils import build_execution_name


class WorkflowStartError(RuntimeError):
    """Raised when the Step Functions execution could not be started."""


class StepFunctionsExecutor:
    def __init__(self, config: Config, client: Optional[Any] = None) -> None:
        self._config = config
        self._client = client or boto3.client("stepfunctions")

    def start_execution(
        self,
        execution_request: SearchExecutionRequest,
        trace_header: Optional[str] = None,
    ) -> Dict[str, Any]:
        execution_input = execution_request.to_stepfunctions_input()
        execution_name = build_execution_name(
            self._config.execution_name_prefix,
            execution_request.search_id,
            execution_request.user_id,
        )

        params: Dict[str, Any] = {
            "stateMachineArn": self._config.state_machine_arn,
            "name": execution_name,
            "input": json.dumps(execution_input),
        }
        if trace_header:
            params["traceHeader"] = trace_header

        try:
            response = self._client.start_execution(**params)
        except (ClientError, BotoCoreError) as exc:
            raise WorkflowStartError(str(exc)) from exc

        response["executionName"] = execution_name
        return response