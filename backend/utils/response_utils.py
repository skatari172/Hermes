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
        conversation_history = context_data.get("conversation_history", [])
        
        # Build conversation history context
        conversation_context = ""
        if conversation_history:
            conversation_context = "\n\nPrevious Conversation:\n"
            for turn in conversation_history[-5:]:  # Last 5 messages
                role = turn.get("role", "unknown")
                message = turn.get("message", "")
                conversation_context += f"{role}: {message}\n"
        
        # Check if this is an initial photo analysis or a follow-up chat message
        is_followup = len(conversation_history) > 0 and user_message != "Tell me about what I'm seeing in this photo"
        
        if is_followup:
            # For follow-up messages: Keep it very concise (1-4 sentences)
            prompt = f"""You are Hermes, an AI cultural companion. Answer the user's question concisely.

CONTEXT:
- Entity: {entity}
- Location: {coordinates.get('lat', 'Unknown')}, {coordinates.get('lng', 'Unknown')}
- Cultural Summary: {cultural_summary}{conversation_context}

USER QUESTION: {user_message}

CRITICAL INSTRUCTIONS:
- NEVER mention coordinates, latitude, longitude, or GPS data in your response
- You may mention the city or region if relevant
- Keep response to 1-2 sentences for simple questions, 3-4 sentences max for complex questions
- Be professional and factual
- If referencing the photo, be brief
- Answer directly without unnecessary elaboration"""
        else:
            # For initial photo analysis: Structured but concise sections
            prompt = f"""You are Hermes, an AI cultural companion. Analyze this photo professionally.

CONTEXT:
- Entity: {entity}
- Location: {coordinates.get('lat', 'Unknown')}, {coordinates.get('lng', 'Unknown')}
- Cultural Summary: {cultural_summary}{conversation_context}

USER MESSAGE: {user_message}

Format your response with these brief sections:
1. **What You're Seeing**: (1-2 sentences identifying the main subject)
2. **Cultural Context**: (1-2 sentences about historical/cultural significance)
3. **Key Facts**: (1-2 sentences with interesting details)
4. **Recommendation**: (1-2 sentences if applicable)

CRITICAL GUIDELINES:
- NEVER mention coordinates, latitude, longitude, or GPS data
- You may mention the city or region if relevant to cultural context
- Be professional, not overly enthusiastic
- Keep each section to 1-2 sentences maximum
- Focus on factual information
- Maintain a knowledgeable but concise tone"""
        
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

