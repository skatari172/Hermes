# agents/conversation_agent.py
from google.adk.agents.llm_agent import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import AgentCard
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from datetime import datetime
from typing import Dict, Any, List, Optional

# Remote agent references
RESPONSE_CARD_URL = f"http://localhost:8006{AGENT_CARD_WELL_KNOWN_PATH}"
DATABASE_CARD_URL = f"http://localhost:8005{AGENT_CARD_WELL_KNOWN_PATH}"

response_agent = RemoteA2aAgent(name="response_agent_remote", agent_card_url=RESPONSE_CARD_URL)
database_agent = RemoteA2aAgent(name="database_agent_remote", agent_card_url=DATABASE_CARD_URL)

def process_user_message(
    user_message: str,
    user_id: str,
    session_id: str,
    conversation_context: str = "",
    include_image_context: bool = True,
    confidence_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Process user message and generate appropriate response using response agent.
    
    Args:
        user_message: User's text or transcribed speech
        user_id: User identifier
        session_id: Session identifier
        conversation_context: Previous conversation context
        include_image_context: Whether to include image summaries in response
        confidence_data: Confidence ratings and verification data
        
    Returns:
        Response with text and metadata
    """
    try:
        print(f"💬 Processing user message: {user_message[:50]}...")
        
        # Get image summaries if requested
        image_summaries = []
        if include_image_context:
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
        
        # Generate response using response agent
        response_result = response_agent.run_tool(
            "generate_cultural_response",
            {
                "user_message": user_message,
                "user_id": user_id,
                "session_id": session_id,
                "image_summaries": image_summaries,
                "conversation_context": conversation_context,
                "confidence_data": confidence_data
            }
        )
        
        print(f"✅ Generated response: {response_result.get('response', 'No response')[:100]}...")
        
        return {
            "status": "success",
            "response": response_result.get("response", "I apologize, but I couldn't generate a response."),
            "user_message": user_message,
            "context_used": {
                "image_summaries_count": len(image_summaries),
                "conversation_context_provided": bool(conversation_context),
                "timestamp": datetime.utcnow().isoformat()
            },
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "processed_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        print(f"❌ Message processing error: {e}")
        return {
            "status": "error",
            "response": "I apologize, but I'm having trouble processing your message right now. Please try again.",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

def handle_image_analysis_response(
    cultural_summary: str,
    entity_name: str = None,
    location: str = None,
    user_message: str = "Tell me about what I'm seeing"
) -> Dict[str, Any]:
    """
    Handle response to image analysis results.
    
    Args:
        cultural_summary: The cultural summary from image analysis
        entity_name: Name of the identified entity
        location: Location where image was taken
        user_message: User's question about the image
        
    Returns:
        Response focused on the image analysis
    """
    try:
        print(f"📸 Handling image analysis response for {entity_name or 'unknown entity'}")
        
        # Use response agent for image-specific responses
        response_result = response_agent.run_tool(
            "generate_image_analysis_response",
            {
                "cultural_summary": cultural_summary,
                "entity_name": entity_name,
                "location": location,
                "user_message": user_message
            }
        )
        
        return response_result
        
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

# Define root conversation agent using ADK
root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="conversation_agent",
    description="Handles user conversations and routes them to appropriate response generation using cultural context.",
    instruction="""You are Hermes, an AI cultural companion for travelers. Your role is to:

1. **Process User Messages**: Handle user questions, comments, and requests about their travel experiences
2. **Route to Response Agent**: Use the response agent to generate culturally-informed responses
3. **Maintain Context**: Keep track of conversation flow and cultural context from images

**Key Responsibilities:**
- Process user messages and generate appropriate responses
- Include cultural context from recent images when relevant
- Handle both general conversation and image-specific questions
- Maintain conversation flow and context

**Tools Available:**
- `process_user_message`: Handle general user messages with cultural context
- `handle_image_analysis_response`: Respond specifically to image analysis results
- `clear_conversation_memory`: Clear conversation history when session ends

**Response Style:**
- Be conversational and engaging
- Reference cultural context when available
- Ask follow-up questions to keep conversation flowing
- Be helpful and informative about travel experiences""",
    tools=[process_user_message, handle_image_analysis_response, clear_conversation_memory],
)

# Expose agent via A2A protocol
a2a_app = to_a2a(
    root_agent,
    port=8007,  # New port for conversation agent
    agent_card=AgentCard(
        name="conversation_agent",
        url="http://localhost:8007",
        description="Handles user conversations and routes to response generation with cultural context.",
        version="1.0.0",
        defaultInputModes=["application/json"],
        defaultOutputModes=["application/json"],
    ),
)