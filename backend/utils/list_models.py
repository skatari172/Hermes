#!/usr/bin/env python3
"""
List available Gemini models
"""

import os
import google.generativeai as genai  # pyright: ignore[reportMissingImports]
from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]

# Load environment variables
load_dotenv()

def list_models():
    """List all available Gemini models"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY not found")
        return
    
    genai.configure(api_key=api_key)
    
    print("🔍 Available Gemini Models:")
    print("=" * 40)
    
    try:
        models = genai.list_models()
        for model in models:
            print(f"📝 {model.name}")
            if hasattr(model, 'supported_generation_methods'):
                print(f"   Methods: {model.supported_generation_methods}")
            print()
    except Exception as e:
        print(f"❌ Error listing models: {e}")

if __name__ == "__main__":
    list_models()
