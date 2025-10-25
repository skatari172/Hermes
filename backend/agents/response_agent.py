# agents/response_agent.py
from google.adk.agents.llm_agent import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import AgentCard
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from datetime import datetime
import json
from typing import Dict, Any, List

# Remote agent references
DATABASE_CARD_URL = f"http://localhost:8005{AGENT_CARD_WELL_KNOWN_PATH}"

database_agent = RemoteA2aAgent(name="database_agent_remote", agent_card_url=DATABASE_CARD_URL)

def generate_cultural_response(
    user_message: str,
    user_id: str,
    session_id: str,
    image_summaries: List[Dict] = None,
    conversation_context: str = ""
) -> Dict[str, Any]:
    """
    Generate a conversational response based on cultural context and user message.
    
    Args:
        user_message: What the user asked or said
        user_id: User identifier
        session_id: Session identifier
        image_summaries: List of cultural summaries from images
        conversation_context: Additional conversation context
        
    Returns:
        Response with text and metadata
    """
    try:
        print(f"🤖 Generating response for user {user_id}: {user_message[:50]}...")
        
        # If no image summaries provided, try to retrieve them
        if not image_summaries:
            try:
                summaries_result = database_agent.run_tool(
                    "retrieve_image_summaries",
                    {
                        "user_id": user_id,
                        "session_id": session_id,
                        "limit": 5
                    }
                )
                image_summaries = summaries_result.get("image_summaries", [])
                print(f"📚 Retrieved {len(image_summaries)} image summaries for context")
            except Exception as e:
                print(f"⚠️ Could not retrieve image summaries: {e}")
                image_summaries = []
        
        # Build context for the LLM
        context_prompt = _build_response_context(user_message, image_summaries, conversation_context)
        
        # Generate response using Gemini
        from google.genai import GenerativeModel
        model = GenerativeModel("gemini-2.5-flash")
        
        response = model.generate_content(context_prompt)
        response_text = response.text.strip()
        
        print(f"✅ Generated response: {response_text[:100]}...")
        
        return {
            "status": "success",
            "response": response_text,
            "user_message": user_message,
            "context_used": {
                "image_summaries_count": len(image_summaries),
                "conversation_context_provided": bool(conversation_context),
                "timestamp": datetime.utcnow().isoformat()
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
            "status": "error",
            "response": "I apologize, but I'm having trouble generating a response right now. Please try again.",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

def _build_response_context(user_message: str, image_summaries: List[Dict], conversation_context: str) -> str:
    """Build comprehensive context prompt for response generation."""
    
    context_parts = []
    
    # Add persona and instructions
    context_parts.append("""You are Hermes, an AI cultural companion for travelers. You help people understand and appreciate the cultural and historical significance of what they're seeing during their travels.

Your personality:
- Enthusiastic and knowledgeable about culture and history
- Conversational and engaging, not academic or dry
- Helpful and encouraging
- Respectful of different cultures and traditions
- Able to make connections between what they see and broader cultural context

Your role:
- Answer questions about cultural sites, historical events, and local traditions
- Provide context about what they're seeing in their photos
- Share interesting facts and stories
- Help them understand the significance of their travel experiences""")
    
    # Add image context if available
    if image_summaries:
        context_parts.append("\n**Cultural Context from Recent Images:**")
        for i, summary in enumerate(image_summaries[:3], 1):  # Limit to 3 most recent
            cultural_summary = summary.get("cultural_summary", "")
            entity_name = summary.get("entity_name", "Unknown")
            location = summary.get("location", "Unknown location")
            
            context_parts.append(f"Image {i}: {entity_name} at {location}")
            context_parts.append(f"Cultural context: {cultural_summary}")
            context_parts.append("")
    else:
        context_parts.append("\n**No recent image context available.**")
    
    # Add conversation context if provided
    if conversation_context:
        context_parts.append(f"**Recent Conversation Context:** {conversation_context}")
    
    # Add user's current message
    context_parts.append(f"\n**User's Current Message:** {user_message}")
    
    # Add response guidelines
    context_parts.append("""
**Response Guidelines:**
- Keep responses conversational and engaging (2-4 sentences typically)
- If they're asking about something in their recent images, reference that context
- If they're asking about something not in recent images, provide general helpful information
- Be enthusiastic about cultural and historical topics
- Use "you" to make it personal and engaging
- If you don't know something specific, acknowledge it and offer general information
- End responses in a way that invites further conversation

**Example Response Style:**
"That's a fascinating question! The Eiffel Tower you photographed earlier has such an interesting history - it was actually built as a temporary structure for the 1889 World's Fair. What other aspects of Parisian culture are you curious about?" """)
    
    return "\n".join(context_parts)

def generate_image_analysis_response(
    cultural_summary: str,
    entity_name: str = None,
    location: str = None,
    user_message: str = "Tell me about what I'm seeing"
) -> Dict[str, Any]:
    """
    Generate a response specifically for image analysis results.
    
    Args:
        cultural_summary: The cultural summary from image analysis
        entity_name: Name of the identified entity
        location: Location where image was taken
        user_message: User's question about the image
        
    Returns:
        Response focused on the image analysis
    """
    try:
        print(f"📸 Generating image analysis response for {entity_name or 'unknown entity'}")
        
        context_prompt = f"""You are Hermes, an AI cultural companion. A traveler has taken a photo and you've analyzed it. 

**Image Analysis Results:**
- Entity: {entity_name or 'Not identified'}
- Location: {location or 'Unknown location'}
- Cultural Summary: {cultural_summary}

**User's Question:** {user_message}

**Your Task:** Provide an engaging, conversational response that:
- Shares the most interesting cultural/historical information from the analysis
- Answers their specific question if possible
- Makes them excited about what they're seeing
- Connects the specific site to broader cultural context
- Invites them to learn more or ask follow-up questions

**Response Style:** Be enthusiastic, conversational, and educational. Use "you" to make it personal."""

        from google.genai import GenerativeModel
        model = GenerativeModel("gemini-2.5-flash")
        
        response = model.generate_content(context_prompt)
        response_text = response.text.strip()
        
        return {
            "status": "success",
            "response": response_text,
            "image_context": {
                "entity_name": entity_name,
                "location": location,
                "cultural_summary": cultural_summary
            },
            "user_message": user_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Image analysis response error: {e}")
        return {
            "status": "error",
            "response": "I can see something interesting in your photo! Let me share what I know about this cultural site.",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

def clear_conversation_memory(user_id: str, session_id: str) -> Dict[str, Any]:
    """
    Clear conversation memory for a session.
    Note: This clears in-memory conversation history, not database image summaries.
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        
    Returns:
        Clear operation result
    """
    try:
        print(f"🗑️ Clearing conversation memory for session {session_id}")
        
        # Note: Image summaries in database are preserved
        # Only conversation memory is cleared
        
        return {
            "status": "cleared",
            "user_id": user_id,
            "session_id": session_id,
            "note": "Conversation memory cleared. Image summaries preserved in database.",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Memory clear error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="response_agent",
    description="Generates conversational responses as Hermes, the AI cultural companion, using image cultural summaries and conversation context.",
    instruction="""You are Hermes, an AI cultural companion for travelers. Your role is to:

**Core Identity:**
- Enthusiastic and knowledgeable about culture and history
- Conversational and engaging, not academic or dry
- Helpful and encouraging
- Respectful of different cultures and traditions
- Able to make connections between what they see and broader cultural context

**Core Tasks:**
1. **Cultural Response Generation**: Create engaging responses about cultural and historical topics
2. **Context Integration**: Reference image cultural summaries when relevant
3. **User Engagement**: Answer user questions about what they're seeing
4. **Personality Maintenance**: Keep enthusiastic, knowledgeable personality as Hermes

**Tools Available:**
- `generate_cultural_response`: Generate engaging conversational responses about cultural and historical topics
- `generate_image_analysis_response`: Respond specifically to image analysis results
- `clear_conversation_memory`: Clear conversation history when session ends

**Response Guidelines:**
- Keep responses conversational and engaging (2-4 sentences typically)
- If they're asking about something in their recent images, reference that context
- If they're asking about something not in recent images, provide general helpful information
- Be enthusiastic about cultural and historical topics
- Use "you" to make it personal and engaging
- If you don't know something specific, acknowledge it and offer general information
- End responses in a way that invites further conversation

**Example Response Style:**
"That's a fascinating question! The Eiffel Tower you photographed earlier has such an interesting history - it was actually built as a temporary structure for the 1889 World's Fair. What other aspects of Parisian culture are you curious about?"

**Important:** Always maintain the Hermes personality and reference cultural context when available.""",
    tools=[generate_cultural_response, generate_image_analysis_response, clear_conversation_memory],
)

a2a_app = to_a2a(
    root_agent,
    port=8006,
    agent_card=AgentCard(
        name="response_agent",
        url="http://localhost:8006",
        description="Generates conversational responses as Hermes cultural companion using image summaries.",
        version="1.0.0",
        defaultInputModes=["application/json"],
        defaultOutputModes=["application/json"],
    ),
)
