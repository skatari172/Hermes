#!/usr/bin/env python3
"""
Test script for Gemini LLM client connection
Run this to verify your Gemini API key and connection are working
"""

import os
import sys
from dotenv import load_dotenv

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

def test_gemini_connection():
    """Test Gemini API connection"""
    print("🧪 Testing Gemini LLM Client Connection...")
    print("=" * 50)
    
    # Check if API key exists
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not found in .env file")
        print("Please add your Gemini API key to the .env file:")
        print("GEMINI_API_KEY=your_actual_api_key_here")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        # Import and test Gemini client
        from gemini_client import GeminiClient
        
        print("📡 Initializing Gemini client...")
        client = GeminiClient()
        
        print("🔍 Testing basic text generation...")
        response = client.generate_text("Hello! Please respond with 'Connection successful!'")
        print(f"📝 Response: {response}")
        
        print("🧪 Running connection test...")
        is_working = client.test_connection()
        
        if is_working:
            print("✅ SUCCESS: Gemini LLM client is working correctly!")
            print("🎉 You can now use Gemini for your Hermes project!")
            return True
        else:
            print("❌ FAILED: Connection test did not pass")
            return False
            
    except ImportError as e:
        print(f"❌ ERROR: Failed to import Gemini client: {e}")
        print("Make sure you have installed: pip install google-generativeai")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_environment():
    """Test environment setup"""
    print("🔧 Testing Environment Setup...")
    print("=" * 30)
    
    # Check Python version
    python_version = sys.version_info
    print(f"🐍 Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Check if .env file exists
    env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_file):
        print("✅ .env file found")
    else:
        print("❌ .env file not found")
        return False
    
    # Check required packages
    try:
        import google.generativeai
        print("✅ google-generativeai package installed")
    except ImportError:
        print("❌ google-generativeai package not installed")
        print("Install with: pip install google-generativeai")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Hermes Gemini LLM Client Test")
    print("=" * 40)
    
    # Test environment first
    if not test_environment():
        print("\n❌ Environment test failed. Please fix the issues above.")
        sys.exit(1)
    
    print("\n" + "=" * 40)
    
    # Test Gemini connection
    if test_gemini_connection():
        print("\n🎉 All tests passed! Your Gemini client is ready to use.")
        sys.exit(0)
    else:
        print("\n❌ Gemini connection test failed. Please check your API key.")
        sys.exit(1)
