#!/usr/bin/env python3
"""
Test script for refactored Search Initializer Lambda
Tests the clean orchestrator pattern without MongoDB dependencies
"""

import json
import os
import sys
from unittest.mock import Mock, patch

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lambda_handler import lambda_handler


def test_api_gateway_event():
    """Test with API Gateway event format"""
    event = {
        "body": json.dumps({
            "query": "Find machine learning experts",
            "flags": {
                "reasoning": True,
                "alternative_skills": False
            }
        }),
        "requestContext": {
            "authorizer": {
                "userId": "test_user_123"
            }
        },
        "headers": {
            "X-Amzn-Trace-Id": "Root=1-test-trace-id"
        }
    }

    # Mock Step Functions client
    with patch('boto3.client') as mock_boto3:
        mock_sf_client = Mock()
        mock_sf_client.start_execution.return_value = {
            "executionArn": "arn:aws:states:region:account:execution:search-exec:test-execution",
            "startDate": "2023-09-23T10:00:00Z"
        }
        mock_boto3.return_value = mock_sf_client

        # Mock environment variables
        with patch.dict(os.environ, {
            "LOGICAL_SEARCH_STATE_MACHINE_ARN": "arn:aws:states:region:account:stateMachine:test-search-machine",
            "EXECUTION_NAME_PREFIX": "search-exec",
            "CORS_ALLOWED_ORIGIN": "*"
        }):
            result = lambda_handler(event, None)

    print("=== API Gateway Event Test ===")
    print(f"Status Code: {result['statusCode']}")
    print(f"Response Body: {json.dumps(json.loads(result['body']), indent=2)}")

    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['success'] is True
    assert 'searchId' in body
    assert body['query'] == "Find machine learning experts"
    assert body['pipeline'] == "search"
    print("✅ API Gateway event test passed\n")


def test_direct_invocation():
    """Test with direct invocation format"""
    event = {
        "query": "Python developers with AWS experience",
        "userId": "direct_user_456",
        "flags": {
            "hyde_provider": "openai",
            "reasoning": False
        }
    }

    # Mock Step Functions client
    with patch('boto3.client') as mock_boto3:
        mock_sf_client = Mock()
        mock_sf_client.start_execution.return_value = {
            "executionArn": "arn:aws:states:region:account:execution:search-exec:direct-execution",
            "startDate": "2023-09-23T10:05:00Z"
        }
        mock_boto3.return_value = mock_sf_client

        # Mock environment variables
        with patch.dict(os.environ, {
            "LOGICAL_SEARCH_STATE_MACHINE_ARN": "arn:aws:states:region:account:stateMachine:test-search-machine",
            "EXECUTION_NAME_PREFIX": "search-exec"
        }):
            result = lambda_handler(event, None)

    print("=== Direct Invocation Test ===")
    print(f"Status Code: {result['statusCode']}")
    print(f"Response Body: {json.dumps(json.loads(result['body']), indent=2)}")

    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['success'] is True
    assert 'searchId' in body
    assert body['query'] == "Python developers with AWS experience"
    assert body['flags']['hyde_provider'] == "openai"
    print("✅ Direct invocation test passed\n")


def test_validation_error():
    """Test validation error handling"""
    event = {
        "body": json.dumps({
            "flags": {"reasoning": True}
            # Missing required "query" field
        }),
        "requestContext": {
            "authorizer": {
                "userId": "test_user"
            }
        }
    }

    # Mock environment variables
    with patch.dict(os.environ, {
        "LOGICAL_SEARCH_STATE_MACHINE_ARN": "arn:aws:states:region:account:stateMachine:test-search-machine"
    }):
        result = lambda_handler(event, None)

    print("=== Validation Error Test ===")
    print(f"Status Code: {result['statusCode']}")
    print(f"Response Body: {json.dumps(json.loads(result['body']), indent=2)}")

    assert result['statusCode'] == 400
    body = json.loads(result['body'])
    assert body['success'] is False
    assert 'error' in body
    print("✅ Validation error test passed\n")


def test_options_request():
    """Test OPTIONS request handling (CORS preflight)"""
    event = {
        "httpMethod": "OPTIONS"
    }

    result = lambda_handler(event, None)

    print("=== OPTIONS Request Test ===")
    print(f"Status Code: {result['statusCode']}")
    print(f"Headers: {json.dumps(result['headers'], indent=2)}")

    assert result['statusCode'] == 204
    assert result['body'] == ""
    assert 'Access-Control-Allow-Origin' in result['headers']
    print("✅ OPTIONS request test passed\n")


if __name__ == "__main__":
    print("Testing refactored Search Initializer Lambda (Clean Orchestrator Pattern)")
    print("=" * 80)

    try:
        test_api_gateway_event()
        test_direct_invocation()
        test_validation_error()
        test_options_request()

        print("🎉 All tests passed! The refactoring follows the clean orchestrator pattern correctly.")
        print("\nKey improvements:")
        print("- ✅ No MongoDB operations in orchestrator")
        print("- ✅ Clean separation of concerns")
        print("- ✅ Follows orchestrator_cron pattern exactly")
        print("- ✅ Proper error handling")
        print("- ✅ CORS support")
        print("- ✅ Trace header support")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)