# agents/database_agent.py
from google.adk.agents.llm_agent import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import AgentCard
from datetime import datetime
import json
from typing import Dict, Any, List

def store_image_cultural_summary(context_data: dict, user_id: str, session_id: str) -> dict:
    """
    Store cultural summary of a single image in database.
    Only stores the complete cultural summary, not conversation history.
    
    Args:
        context_data: Combined data from perception, wiki, and geo agents
        user_id: User identifier
        session_id: Session identifier
        
    Returns:
        Storage result with summary_id
    """
    try:
        # Create cultural summary from all context data
        cultural_summary = _create_cultural_summary(context_data)
        
        # Only store the essential cultural summary data
        image_summary = {
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "cultural_summary": cultural_summary,
            "entity_verified": context_data.get('verified', False),
            "entity_name": context_data.get('entity'),
            "entity_type": context_data.get('entity_type'),
            "certainty_score": context_data.get('certainty', 0.0),
            "location": context_data.get('geo_context', {}).get('address', 'Unknown location')
        }
        
        # Generate unique summary ID
        summary_id = f"{user_id}_{session_id}_{int(datetime.utcnow().timestamp())}"
        image_summary["summary_id"] = summary_id
        
        # TODO: Store in your database (Firestore, PostgreSQL, etc.)
        # For now, we'll simulate successful storage
        print(f"📝 Stored image cultural summary: {summary_id}")
        print(f"📝 Summary: {cultural_summary[:100]}...")
        
        return {
            "status": "stored",
            "summary_id": summary_id,
            "cultural_summary": cultural_summary,
            "timestamp": image_summary["timestamp"]
        }
        
    except Exception as e:
        print(f"❌ Database storage error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

def _create_cultural_summary(context_data: dict) -> str:
    """Create a concise cultural summary from all context data."""
    try:
        perception = context_data.get('perception', {})
        wiki_facts = context_data.get('wiki_facts', [])
        geo_context = context_data.get('geo_context', {})
        
        summary_parts = []
        
        # Add location context
        if geo_context.get('address'):
            summary_parts.append(f"Location: {geo_context['address']}")
        
        # Add scene description
        if perception.get('scene_summary'):
            summary_parts.append(f"Scene: {perception['scene_summary']}")
        
        # Add cultural elements
        if perception.get('cultural_notes'):
            cultural_notes = perception['cultural_notes']
            if isinstance(cultural_notes, list) and cultural_notes:
                summary_parts.append(f"Cultural elements: {', '.join(cultural_notes[:3])}")
        
        # Add historical/cultural facts
        if wiki_facts:
            for fact in wiki_facts[:2]:  # Limit to top 2 facts
                if fact.get('is_cultural_content', False):
                    extract = fact.get('extract', '')
                    if extract:
                        # Truncate long extracts
                        if len(extract) > 150:
                            extract = extract[:150] + "..."
                        summary_parts.append(f"Historical context: {extract}")
        
        # Add detected text if relevant
        if perception.get('text_analysis'):
            text_items = perception['text_analysis']
            if isinstance(text_items, list) and text_items:
                detected_texts = [item.get('detected_text', '') for item in text_items[:2]]
                summary_parts.append(f"Detected text: {', '.join(detected_texts)}")
        
        return " | ".join(summary_parts) if summary_parts else "No significant cultural context identified"
        
    except Exception as e:
        print(f"⚠️ Summary creation error: {e}")
        return "Cultural context summary unavailable"

def retrieve_image_summaries(user_id: str, session_id: str = None, limit: int = 10) -> dict:
    """
    Retrieve stored image cultural summaries for a user or session.
    Only returns image summaries, not conversation history.
    
    Args:
        user_id: User identifier
        session_id: Optional session identifier
        limit: Maximum number of summaries to return
        
    Returns:
        List of image cultural summaries
    """
    try:
        # TODO: Query your database for stored image summaries
        # For now, return empty list
        print(f"🔍 Retrieving image cultural summaries for user {user_id}")
        
        return {
            "status": "success",
            "image_summaries": [],  # Would contain actual image summaries from database
            "count": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Retrieval error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "image_summaries": [],
            "count": 0
        }

def clear_session_image_summaries(user_id: str, session_id: str) -> dict:
    """
    Clear image cultural summaries for a specific session.
    Note: Conversation history is handled in memory, not in database.
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        
    Returns:
        Clear operation result
    """
    try:
        # TODO: Delete image summaries from database for this session
        print(f"🗑️ Clearing image cultural summaries for session {session_id}")
        
        return {
            "status": "cleared",
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Clear error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="database_agent",
    description="Manages image cultural summary storage and retrieval. Only stores image summaries, not conversation history.",
    instruction="""You are the Database Agent in the Hermes AI travel companion system. Your role is to:

**Core Tasks:**
1. **Image Summary Storage**: Store cultural summaries from image analysis (one summary per image)
2. **Summary Retrieval**: Retrieve image summaries for context when needed
3. **Session Management**: Clear image summaries when session ends
4. **Data Integrity**: Ensure only cultural summaries are stored, not conversation history

**Tools Available:**
- `store_image_cultural_summary`: Store cultural summaries from image analysis
- `retrieve_image_summaries`: Retrieve image summaries for context
- `clear_session_image_summaries`: Clear image summaries when session ends

**Storage Structure:**
Each image summary contains:
- user_id: User identifier
- session_id: Session identifier
- timestamp: When summary was created
- cultural_summary: Complete cultural summary text
- entity_verified: Whether entity was verified
- entity_name: Name of identified entity
- entity_type: Type of entity
- certainty_score: Confidence in identification
- location: Geographic location
- summary_id: Unique identifier

**Important Notes:**
- Only stores image cultural summaries, NOT conversation history
- Conversation history is handled in memory and cleared after session
- Focus on preserving cultural and historical insights for travelers
- Each image gets one summary entry""",
    tools=[store_image_cultural_summary, retrieve_image_summaries, clear_session_image_summaries],
)

a2a_app = to_a2a(
    root_agent,
    port=8005,
    agent_card=AgentCard(
        name="database_agent",
        url="http://localhost:8005",
        description="Image cultural summary storage and retrieval. Only stores image summaries, not conversation history.",
        version="1.0.0",
        defaultInputModes=["application/json"],
        defaultOutputModes=["application/json"],
    ),
)
