"""
Response Agent Utilities
Standalone functions for generating cultural responses
"""
import os
import re
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
        conversation_history = context_data.get("conversation_history", [])
        
        # Build conversation history context
        conversation_context = ""
        if conversation_history:
            conversation_context = "\n\nPrevious Conversation:\n"
            for turn in conversation_history[-5:]:  # Last 5 messages
                role = turn.get("role", "unknown")
                message = turn.get("message", "")
                conversation_context += f"{role}: {message}\n"
        
        # For chat messages: Keep responses to 2-3 sentences maximum
        prompt = f"""You are Hermes. Answer this question in 2-3 sentences maximum.

Question: {user_message}

RULES:
1. Write exactly 2-3 sentences only
2. NO asterisks, NO bold, NO formatting
3. NO section headers like "What You're Seeing"
4. Plain text - just answer directly
5. Do NOT mention coordinates, latitude, or longitude
6. Be concise and helpful

Example response: "Orlando has great spots. Universal Studios offers thrilling rides while Lake Eola Park provides a peaceful downtown escape. Both showcase the city's diverse attractions."

Now answer the user's question in 2-3 sentences: {user_message}"""
        
        response = model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": 50,  # Limit response tokens
                "temperature": 0.7
            }
        )
        response_text = response.text.strip()
        
        # Clean up formatting - remove asterisks and markdown
        response_text = re.sub(r'\*\*', '', response_text)  # Remove bold markers
        response_text = re.sub(r'\*', '', response_text)  # Remove any other asterisks
        response_text = re.sub(r'#+\s*', '', response_text)  # Remove headers
        response_text = response_text.strip()
        
        # Enforce 2-3 sentence limit
        sentences = re.split(r'[.!?]+', response_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) > 3:
            response_text = ". ".join(sentences[:3]) + "."
        
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

