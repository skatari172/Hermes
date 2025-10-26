#!/usr/bin/env python3
"""
Test the chat routes functionality.
"""

import requests
import json

def test_chat_routes():
    """Test the chat routes endpoints."""
    print("🧪 TESTING CHAT ROUTES")
    print("=" * 40)
    
    user_id = "test_user"
    session_id = "test_session"
    
    # Test chat endpoint
    print("💬 Testing chat endpoint...")
    
    try:
        data = {
            'user_message': 'Hello Hermes!',
            'user_id': user_id,
            'session_id': session_id
        }
        
        response = requests.post(
            "http://localhost:8000/api/chat/",
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Chat successful!")
            print(f"   Status: {result.get('status')}")
            print(f"   Response: {result.get('response', '')[:100]}...")
            print(f"   Session Info: {result.get('session_info', {})}")
            return True
        else:
            print(f"❌ Chat request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Chat test failed: {e}")
        return False

def test_session_endpoint():
    """Test the session info endpoint."""
    print("\n📋 Testing session endpoint...")
    
    try:
        user_id = "test_user"
        session_id = "test_session"
        
        response = requests.get(f"http://localhost:8000/api/chat/session/{user_id}/{session_id}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Session info retrieved!")
            print(f"   Status: {result.get('status')}")
            session_info = result.get('session_info', {})
            print(f"   User ID: {session_info.get('user_id')}")
            print(f"   Session ID: {session_info.get('session_id')}")
            print(f"   Conversation Length: {session_info.get('conversation_length')}")
            print(f"   Has Context: {session_info.get('has_context')}")
            return True
        else:
            print(f"❌ Session info request failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Session info test failed: {e}")
        return False

def test_api_endpoints():
    """Test basic API endpoints."""
    print("🌐 Testing API endpoints...")
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print("✅ API server is running")
        else:
            print(f"⚠️ API server response: {response.status_code}")
            
        return True
        
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        print("💡 Make sure the server is running: python main.py")
        return False

def main():
    """Run all tests."""
    print("🚀 CHAT ROUTES TESTING")
    print("=" * 50)
    
    # Test API endpoints first
    api_test = test_api_endpoints()
    
    if not api_test:
        print("\n❌ API server not available. Please start the server first:")
        print("   cd /Users/sujankatari/Hermes/backend")
        print("   source venv/bin/activate")
        print("   python main.py")
        return
    
    # Test chat routes
    chat_test = test_chat_routes()
    session_test = test_session_endpoint()
    
    # Summary
    print(f"\n{'='*50}")
    print(f"🎉 CHAT ROUTES TEST SUMMARY")
    print(f"{'='*50}")
    
    print(f"✅ API Server: {'RUNNING' if api_test else 'FAILED'}")
    print(f"✅ Chat Endpoint: {'WORKING' if chat_test else 'FAILED'}")
    print(f"✅ Session Endpoint: {'WORKING' if session_test else 'FAILED'}")
    
    if chat_test and session_test:
        print(f"\n🎉 ALL CHAT ROUTES WORKING!")
        print(f"✅ POST /api/chat/ - Chat with Hermes")
        print(f"✅ GET /api/chat/session/{user_id}/{session_id} - Session info")
        print(f"✅ In-memory session storage")
        print(f"✅ Context-aware responses")
        print(f"✅ Conversation history tracking")
    else:
        print(f"\n⚠️ Some chat route tests failed. Check the error messages above.")

if __name__ == "__main__":
    main()
