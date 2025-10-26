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
        
        # Extract geo context from context_data - check multiple possible keys
        geo_context = (
            context_data.get("geo_context", {}) or 
            context_data.get("geo", {}) or 
            context_data.get("location_api", {})
        )
        
        # Debug: print ALL context data to see what's available
        print(f"🔍 DEBUG: context_data keys = {list(context_data.keys())}")
        print(f"🔍 DEBUG: Full context_data = {context_data}")
        if geo_context:
            print(f"📍 Geo context extracted: address={geo_context.get('address')}, city={geo_context.get('city')}")
            print(f"🗺️ Nearby landmarks count: {len(geo_context.get('landmarks', []))}")
            print(f"🗺️ Full geo_context = {geo_context}")
        else:
            print("⚠️ No geo context found in context_data")
        
        # Extract location info even if geo_context is empty - try coordinates
        if not geo_context and coordinates:
            print(f"📍 Using raw coordinates: lat={coordinates.get('lat')}, lng={coordinates.get('lng')}")
        
        # Build conversation history context
        conversation_context = ""
        if conversation_history:
            conversation_context = "\n\nPrevious Conversation:\n"
            for turn in conversation_history[-5:]:  # Last 5 messages
                role = turn.get("role", "unknown")
                message = turn.get("message", "")
                conversation_context += f"{role}: {message}\n"
        
        # Check if this is an initial photo analysis or a follow-up chat message
        # A follow-up is any message that's not the initial photo analysis prompt
        is_followup = user_message != "Tell me about what I'm seeing in this photo"
        
        if is_followup:
            # For follow-up messages: ULTRA CONCISE - 2-3 sentences, MAX 20 words
            prompt = f"""You are Hermes. Answer in 2-3 sentences MAX, under 20 words.

CONTEXT: {cultural_summary[:100]}
QUESTION: {user_message}

RULES:
- MAX 20 words total - COUNT YOUR WORDS
- 2-3 sentences ONLY
- NO asterisks, NO formatting, NO coordinates
- Be extremely brief and helpful"""
        else:
            # For initial photo analysis: Use full geo context including nearby spots
            # Extract location and nearby attractions from geo_context
            if geo_context:
                # Handle different geo context formats
                location_name = geo_context.get('address') or geo_context.get('city') or 'this location'
                nearby_spots = geo_context.get('landmarks', [])[:3]
                # Handle different landmark formats (title vs name, with distance_m)
                nearby_text = ", ".join([spot.get('title', spot.get('name', str(spot))) for spot in nearby_spots if isinstance(spot, dict)]) if nearby_spots else "none nearby"
            else:
                # Fallback: use entity or generic location
                location_name = entity if entity != "Unknown Entity" else 'this location'
                nearby_text = "checking location for nearby attractions"
            
            prompt = f"""You are Hermes, an AI cultural companion. Analyze this photo with full geographic context.

CRITICAL - USER'S LOCATION:
- User is at: {location_name}
- Nearby attractions in area: {nearby_text}
- Entity in photo: {entity}
- Cultural context: {cultural_summary[:200]}{conversation_context}

IMPORTANT: The user is physically located at "{location_name}". Use this location context to:
1. Provide location-specific cultural information
2. Recommend nearby attractions ({nearby_text})
3. Make relevant historical/cultural connections to this area

Provide your analysis in these sections:
1. What You're Seeing: (1-2 sentences - identify the main subject)
2. Cultural Context: (1-2 sentences - historical/cultural significance at {location_name})
3. Key Facts: (1-2 sentences - interesting details about this site/location)
4. Nearby Recommendations: (1-2 sentences - mention specific attractions: {nearby_text} if they exist)

CRITICAL OUTPUT RULES:
- NO asterisks in your output - use plain text sections
- NEVER mention coordinates, latitude, longitude, or GPS data
- Always mention the city/location name: {location_name}
- Reference nearby attractions by name
- Be professional and informative
- Keep each section to 1-2 sentences"""
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Remove all asterisks and markdown formatting
        response_text = re.sub(r'\*\*', '', response_text)  # Remove bold markers
        response_text = re.sub(r'\*', '', response_text)  # Remove any other asterisks
        response_text = re.sub(r'#+\s*', '', response_text)  # Remove headers
        
        # ONLY enforce strict limits for follow-up chat messages
        if is_followup:
            # ENFORCE ULTRA-STRICT LIMITS: 20 words max, 2-3 sentences max
            words = response_text.split()
            if len(words) > 20:
                response_text = ' '.join(words[:20])
                # Try to end on a complete sentence
                if not response_text.endswith(('.', '!', '?')):
                    # Find the last sentence boundary
                    last_period = response_text.rfind('.')
                    last_exclamation = response_text.rfind('!')
                    last_question = response_text.rfind('?')
                    last_sentence = max(last_period, last_exclamation, last_question)
                    if last_sentence > 0:
                        response_text = response_text[:last_sentence+1]
                    else:
                        response_text += '.'
            
            # ENFORCE SENTENCE LIMIT: 2-3 sentences max for chat messages
            sentences = re.split(r'[.!?]+', response_text)
            sentences = [s.strip() for s in sentences if s.strip()]
            if len(sentences) > 3:
                response_text = '. '.join(sentences[:3]) + '.'
            elif len(sentences) == 0:
                # If somehow no sentences, just return a truncated version
                response_text = ' '.join(response_text.split()[:20])
        
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

