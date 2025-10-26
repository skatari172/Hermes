"""
Response Agent Utilities
Standalone functions for generating cultural responses
"""
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


async def generate_cultural_response_with_context(user_message: str, context_data: dict, user_id: str, session_id: str) -> dict:
    """Generate cultural response using context data."""
    try:
        print("💬 Generating cultural response...")
        
        # Use Gemini to generate response
        from google.generativeai import GenerativeModel
        import google.generativeai as genai
        
        # Configure API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not found in environment variables")
            return {
                "success": False,
                "error": "Google API key not configured",
                "response": "I apologize, but I couldn't generate a response at this time due to missing API configuration.",
                "user_message": user_message,
                "metadata": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "generated_at": datetime.utcnow().isoformat()
                }
            }
        
        genai.configure(api_key=api_key)
        model = GenerativeModel("gemini-2.5-flash")
        
        # Build context for the prompt
        cultural_summary = context_data.get("cultural_summary", "")
        entity = context_data.get("entity", "Unknown Entity")
        coordinates = context_data.get("coordinates", {})
        
        prompt = f"""You are Hermes, an AI cultural companion for travelers. A user has uploaded a photo and is asking about it.

CONTEXT DATA:
- Entity: {entity}
- Location: {coordinates.get('lat', 'Unknown')}, {coordinates.get('lng', 'Unknown')}
- Cultural Summary: {cultural_summary}

USER MESSAGE: {user_message}

Respond as Hermes with:
1. Warm, engaging personality
2. Cultural and historical insights
3. Travel recommendations
4. Interesting facts about what they're seeing
5. Translation explanations if applicable

Be conversational, informative, and culturally aware. Write as if you're a knowledgeable local guide."""
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        return {
            "success": True,
            "response": response_text,
            "user_message": user_message,
            "context_used": {
                "entity": entity,
                "coordinates": coordinates,
                "cultural_summary_length": len(cultural_summary)
            },
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "response_length": len(response_text),
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        print(f"❌ Response generation error: {e}")
        return {
            "success": False,
            "error": str(e),
            "response": "I apologize, but I couldn't generate a response at this time.",
            "user_message": user_message,
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "generated_at": datetime.utcnow().isoformat()
            }
        }

