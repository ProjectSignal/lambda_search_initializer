"""
Search Initializer Lambda
Creates initial search document and triggers Step Functions workflow
"""

import json
import boto3
import uuid
import os
from datetime import datetime, timezone
from typing import Dict, Any
from pymongo import MongoClient

# Initialize AWS clients
stepfunctions = boto3.client('stepfunctions')

# MongoDB setup
MONGO_URI = os.getenv("MONGODB_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "brace") 
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB_NAME]
searchOutputCollection = mongo_db["searchOutput"]

# Step Functions ARN (to be configured in deployment)
STATE_MACHINE_ARN = os.getenv("LOGICAL_SEARCH_STATE_MACHINE_ARN")

class SearchStatus:
    """Search execution status tracking"""
    NEW = "NEW"
    HYDE_COMPLETE = "HYDE_COMPLETE"
    SEARCH_COMPLETE = "SEARCH_COMPLETE"
    RANK_AND_REASONING_COMPLETE = "RANK_AND_REASONING_COMPLETE"
    ERROR = "ERROR"

def create_initial_search_document(search_id: str, user_id: str, query: str, flags: Dict[str, Any]) -> Dict[str, Any]:
    """Create initial search document in MongoDB"""
    now = datetime.utcnow()
    return {
        "_id": search_id,
        "userId": user_id,
        "query": query,
        "flags": flags,
        "status": SearchStatus.NEW,
        "createdAt": now,
        "updatedAt": now,
        "events": [
            {
                "stage": "INIT",
                "message": "Search initiated",
                "timestamp": now
            }
        ],
        "metrics": {}
    }

def lambda_handler(event, context):
    """
    Initialize logical search and trigger Step Functions workflow
    
    Expected event format (from API Gateway):
    {
        "body": "{\"query\":\"...\", \"flags\":{...}}",
        "requestContext": {
            "authorizer": {
                "userId": "..."
            }
        }
    }
    
    OR direct invocation format:
    {
        "query": "...",
        "flags": {...},
        "userId": "..."
    }
    """
    try:
        # Parse input event
        if 'body' in event:
            # API Gateway format
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
            
            # Extract user ID from authorizer context (API Gateway integration)
            user_id = event.get('requestContext', {}).get('authorizer', {}).get('userId')
            if not user_id:
                # Fallback to body for testing
                user_id = body.get('userId', 'test_user')
        else:
            # Direct invocation format
            body = event
            user_id = event.get('userId')

        # Extract parameters
        query = body.get('query')
        flags = body.get('flags', {})
        
        # Validate required fields
        if not query:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required field: query',
                    'success': False
                })
            }
        
        if not user_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing user authentication',
                    'success': False
                })
            }

        # Generate unique search ID
        search_id = str(uuid.uuid4())
        
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
        
        print(f"Initializing search: {search_id} for user: {user_id}, query: {query}")
        
        # Create initial search document
        search_doc = create_initial_search_document(search_id, user_id, query, final_flags)
        
        try:
            searchOutputCollection.insert_one(search_doc)
            print(f"Created search document: {search_id}")
        except Exception as db_error:
            print(f"Database error: {str(db_error)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': f'Failed to create search document: {str(db_error)}',
                    'success': False
                })
            }
        
        # Prepare Step Functions execution input
        sf_input = {
            'searchId': search_id,
            'userId': user_id,
            'query': query,
            'flags': final_flags,
            'initiatedAt': datetime.utcnow().isoformat()
        }
        
        # Start Step Functions execution
        if STATE_MACHINE_ARN:
            try:
                execution_name = f"search-{search_id}"
                response = stepfunctions.start_execution(
                    stateMachineArn=STATE_MACHINE_ARN,
                    name=execution_name,
                    input=json.dumps(sf_input, default=str)
                )
                
                execution_arn = response['executionArn']
                print(f"Started Step Functions execution: {execution_arn}")
                
                # Update search document with execution ARN
                searchOutputCollection.update_one(
                    {"_id": search_id},
                    {
                        "$set": {
                            "stepFunctionsExecutionArn": execution_arn,
                            "updatedAt": datetime.utcnow()
                        }
                    }
                )
                
            except Exception as sf_error:
                print(f"Step Functions error: {str(sf_error)}")
                # Update search document with error
                searchOutputCollection.update_one(
                    {"_id": search_id},
                    {
                        "$set": {
                            "status": SearchStatus.ERROR,
                            "error": {
                                "stage": "INIT", 
                                "message": f"Failed to start Step Functions: {str(sf_error)}",
                                "occurredAt": datetime.utcnow()
                            }
                        }
                    }
                )
                
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'error': f'Failed to start search execution: {str(sf_error)}',
                        'searchId': search_id,
                        'success': False
                    })
                }
        else:
            print("Warning: STATE_MACHINE_ARN not configured - search document created but workflow not started")
            
        # Return search ID for tracking
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            },
            'body': json.dumps({
                'searchId': search_id,
                'status': 'initiated',
                'message': 'Search pipeline started successfully',
                'query': query,
                'flags': final_flags,
                'success': True,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        print(f"Initialization error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Search initialization failed: {str(e)}',
                'success': False,
                'timestamp': datetime.utcnow().isoformat()
            })
        }

# For local testing
if __name__ == "__main__":
    test_event = {
        "query": "Find experts in machine learning with Python experience",
        "flags": {
            "reasoning": True,
            "alternative_skills": True
        },
        "userId": "test_user_123"
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2, default=str))
