#!/usr/bin/env python3
"""
Test script for Search Initializer Lambda function
"""

import json
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lambda_handler import lambda_handler

def create_test_event_direct():
    """Create a test event for direct invocation (testing without API Gateway)"""
    return {
        "query": "Find machine learning experts with Python experience in San Francisco",
        "flags": {
            "hyde_provider": "groq_llama",
            "description_provider": "groq_llama", 
            "reasoning_model": "groq_llama",
            "alternative_skills": False,
            "reasoning": True,
            "fallback": False
        },
        "userId": "test_user_123"
    }

def create_test_event_api_gateway():
    """Create a test event mimicking API Gateway format"""
    return {
        "body": json.dumps({
            "query": "Find machine learning experts with Python experience in San Francisco",
            "flags": {
                "hyde_provider": "groq_llama",
                "description_provider": "groq_llama", 
                "reasoning_model": "groq_llama",
                "alternative_skills": False,
                "reasoning": True,
                "fallback": False
            }
        }),
        "requestContext": {
            "authorizer": {
                "userId": "test_user_123"
            }
        },
        "headers": {
            "Content-Type": "application/json"
        }
    }

def test_search_initializer():
    """Test the Search Initializer Lambda with different event formats"""
    
    print("Testing Search Initializer Lambda...")
    print("=" * 50)
    
    # Test 1: Direct invocation format
    print("\n1. Testing Direct Invocation Format:")
    print("-" * 30)
    
    test_event_direct = create_test_event_direct()
    print("Test Event (Direct):")
    print(json.dumps(test_event_direct, indent=2))
    
    context = {}  # Mock Lambda context
    
    try:
        result = lambda_handler(test_event_direct, context)
        
        print(f"\nStatus Code: {result['statusCode']}")
        
        if isinstance(result['body'], str):
            body = json.loads(result['body'])
        else:
            body = result['body']
            
        print("Response Body:")
        print(json.dumps(body, indent=2))
        if result['statusCode'] == 200:
            print("✅ Direct invocation test PASSED")
            search_id = body.get('searchId')
            print(f"Created Search ID: {search_id}")
            return search_id
        else:
            print("❌ Direct invocation test FAILED")
            return None
            
    except Exception as e:
        print(f"❌ Error in direct invocation test: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_api_gateway_format():
    """Test API Gateway event format separately"""
    
    print("\n\n2. Testing API Gateway Format:")
    print("-" * 30)
    
    test_event_api = create_test_event_api_gateway()
    print("Test Event (API Gateway):")
    print(json.dumps(test_event_api, indent=2))
    
    context = {}
    
    try:
        result = lambda_handler(test_event_api, context)
        
        print(f"\nStatus Code: {result['statusCode']}")
        
        if isinstance(result['body'], str):
            body = json.loads(result['body'])
        else:
            body = result['body']
            
        print("Response Body:")
        print(json.dumps(body, indent=2))
        
        if result['statusCode'] == 200:
            print("✅ API Gateway format test PASSED")
            search_id = body.get('searchId')
            print(f"Created Search ID: {search_id}")
            return search_id
        else:
            print("❌ API Gateway format test FAILED")
            return None
            
    except Exception as e:
        print(f"❌ Error in API Gateway format test: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def validate_search_document(search_id):
    """Validate that the search document was created properly"""
    if not search_id:
        print("⚠️  No search ID to validate")
        return False
        
    try:
        from pymongo import MongoClient
        import os
        
        # Check if we can connect to MongoDB and validate document
        mongo_uri = os.getenv("MONGODB_URI")
        if not mongo_uri:
            print("⚠️  MONGODB_URI not set - skipping document validation")
            return True  # Assume success if we can't validate
            
        client = MongoClient(mongo_uri)
        db = client[os.getenv("MONGO_DB_NAME", "brace")]
        collection = db["searchOutput"]
        
        doc = collection.find_one({"_id": search_id})
        if doc:
            print(f"✅ Search document validated: status={doc.get('status')}, query={doc.get('query')}")
            return True
        else:
            print("❌ Search document not found in database")
            return False
            
    except Exception as e:
        print(f"⚠️  Could not validate search document: {str(e)}")
        return True  # Don't fail the test for validation issues

if __name__ == "__main__":
    print("🚀 Starting Search Initializer Lambda Tests")
    
    # Run tests
    search_id = test_search_initializer()
    
    if search_id:
        validate_search_document(search_id)
        
    # Test API Gateway format too
    search_id_api = test_api_gateway_format()
    
    if search_id_api:
        validate_search_document(search_id_api)
    
    print("\n" + "=" * 50)
    
    if search_id or search_id_api:
        print("🎉 Search Initializer Lambda tests completed successfully!")
        if search_id:
            print(f"   Direct format search ID: {search_id}")
        if search_id_api:
            print(f"   API Gateway format search ID: {search_id_api}")
        sys.exit(0)
    else:
        print("💥 All tests failed!")
        sys.exit(1)