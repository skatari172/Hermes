# agents/orchestrator_agent.py
from google.adk.agents.llm_agent import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import AgentCard
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from datetime import datetime
import json
from typing import Dict, Any

# Remote agent references
PERCEPTION_CARD_URL = f"http://localhost:8004{AGENT_CARD_WELL_KNOWN_PATH}"
CONTEXT_CARD_URL = f"http://localhost:8003{AGENT_CARD_WELL_KNOWN_PATH}"
DATABASE_CARD_URL = f"http://localhost:8005{AGENT_CARD_WELL_KNOWN_PATH}"

perception_agent = RemoteA2aAgent(name="perception_agent_remote", agent_card_url=PERCEPTION_CARD_URL)
context_agent = RemoteA2aAgent(name="context_agent_remote", agent_card_url=CONTEXT_CARD_URL)
database_agent = RemoteA2aAgent(name="database_agent_remote", agent_card_url=DATABASE_CARD_URL)

def process_image_with_cultural_context(
    image_data: str, 
    lat: float, 
    lng: float, 
    user_id: str, 
    session_id: str,
    image_format: str = "base64",
    radius_meters: int = 1500,
    lang: str = "en"
) -> Dict[str, Any]:
    """
    Complete image processing pipeline:
    1. Perception Agent analyzes the image
    2. Context Agent combines perception + geo + wiki data
    3. Database Agent stores the cultural summary
    
    Args:
        image_data: Base64 encoded image or image URL
        lat: Latitude coordinate
        lng: Longitude coordinate
        user_id: User identifier
        session_id: Session identifier
        image_format: "base64" or "url"
        radius_meters: Search radius for geo context
        lang: Language for wiki searches
        
    Returns:
        Complete cultural context with summary
    """
    try:
        print(f"🔄 Starting image processing pipeline for user {user_id}")
        
        # Step 1: Perception Agent - Analyze the image
        print("📸 Step 1: Analyzing image with Perception Agent...")
        try:
            perception_result = perception_agent.run_tool(
                "analyze_image_perception", 
                {"image_data": image_data, "image_format": image_format}
            )
            print(f"✅ Perception analysis complete: {perception_result.get('scene_summary', 'No summary')[:50]}...")
        except Exception as e:
            print(f"❌ Perception agent error: {e}")
            perception_result = {
                "error": str(e),
                "scene_summary": "Unable to analyze image",
                "detected_objects": [],
                "text_analysis": [],
                "cultural_notes": []
            }
        
        # Step 2: Context Agent - Combine all data
        print("🔗 Step 2: Building context with Context Agent...")
        try:
            context_result = context_agent.run_tool(
                "build_context",
                {
                    "lat": lat,
                    "lng": lng,
                    "perception_clues": perception_result,
                    "image_url": image_data if image_format == "url" else None,
                    "radiusMeters": radius_meters,
                    "lang": lang
                }
            )
            print(f"✅ Context building complete: Entity={context_result.get('entity', 'None')}")
        except Exception as e:
            print(f"❌ Context agent error: {e}")
            context_result = {
                "error": str(e),
                "verified": False,
                "entity": None,
                "geo": {"address": "Unknown", "landmarks": []},
                "facts": []
            }
        
        # Step 3: Database Agent - Store cultural summary
        print("💾 Step 3: Storing cultural summary...")
        try:
            # Prepare context data for storage
            context_data = {
                "perception": perception_result,
                "wiki_facts": context_result.get("facts", []),
                "geo_context": context_result.get("geo", {}),
                "verified": context_result.get("verified", False),
                "entity": context_result.get("entity"),
                "entity_type": context_result.get("entity_type"),
                "certainty": context_result.get("certainty", 0.0)
            }
            
            storage_result = database_agent.run_tool(
                "store_image_cultural_summary",
                {
                    "context_data": context_data,
                    "user_id": user_id,
                    "session_id": session_id
                }
            )
            print(f"✅ Cultural summary stored: {storage_result.get('summary_id', 'Unknown ID')}")
        except Exception as e:
            print(f"❌ Database agent error: {e}")
            storage_result = {
                "status": "error",
                "error": str(e)
            }
        
        # Return complete result
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "session_id": session_id,
            "perception_analysis": perception_result,
            "cultural_context": context_result,
            "storage_result": storage_result,
            "pipeline_summary": {
                "image_analyzed": bool(perception_result.get("scene_summary")),
                "entity_verified": context_result.get("verified", False),
                "entity_name": context_result.get("entity"),
                "cultural_facts_found": len(context_result.get("facts", [])),
                "summary_stored": storage_result.get("status") == "stored"
            }
        }
        
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "session_id": session_id
        }

def get_session_cultural_context(user_id: str, session_id: str) -> Dict[str, Any]:
    """
    Retrieve cultural context summaries for a session.
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        
    Returns:
        Cultural summaries and context
    """
    try:
        print(f"🔍 Retrieving cultural context for session {session_id}")
        
        summaries_result = database_agent.run_tool(
            "retrieve_image_summaries",
            {
                "user_id": user_id,
                "session_id": session_id,
                "limit": 20
            }
        )
        
        return {
            "status": "success",
            "image_summaries": summaries_result.get("image_summaries", []),
            "count": summaries_result.get("count", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Context retrieval error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "image_summaries": [],
            "count": 0
        }

def clear_session_context(user_id: str, session_id: str) -> Dict[str, Any]:
    """
    Clear cultural context for a session.
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        
    Returns:
        Clear operation result
    """
    try:
        print(f"🗑️ Clearing cultural context for session {session_id}")
        
        clear_result = database_agent.run_tool(
            "clear_session_image_summaries",
            {
                "user_id": user_id,
                "session_id": session_id
            }
        )
        
        return clear_result
        
    except Exception as e:
        print(f"❌ Context clear error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="orchestrator_agent",
    description="Orchestrates the full image processing and cultural context storage flow.",
    instruction="""You are the Orchestrator Agent in the Hermes AI travel companion system. Your role is to:

**Core Tasks:**
1. **Image Processing Flow**: Coordinate the sequence of perception, context building, and database storage for images
2. **Agent Coordination**: Manage communication between perception, context, and database agents
3. **Context Retrieval**: Retrieve cultural context for sessions when needed
4. **Session Management**: Clear cultural context when sessions end

**Tools Available:**
- `process_image_flow`: Manage the sequence of perception, context building, and cultural summary storage for images
- `retrieve_session_context`: Retrieve cultural context for a session
- `clear_session_context`: Clear cultural context for a session

**Process Flow for Images:**
1. **Perception Agent**: Analyze the image for visual understanding, text recognition, and cultural cues
2. **Context Agent**: Build comprehensive context by combining perception data with geo and wiki research
3. **Database Agent**: Store the cultural summary for future reference

**Process Flow for Context Retrieval:**
1. Query database for stored image summaries
2. Return formatted cultural context for the session

**Process Flow for Session Cleanup:**
1. Clear stored cultural summaries for the session
2. Confirm cleanup completion

**Important:** Always handle errors gracefully and provide meaningful status updates for each step.""",
    tools=[process_image_flow, retrieve_session_context, clear_session_context],
)

a2a_app = to_a2a(
    root_agent,
    port=8000,  # Main orchestrator on port 8000
    agent_card=AgentCard(
        name="orchestrator_agent",
        url="http://localhost:8000",
        description="Main orchestrator for Hermes cultural context pipeline.",
        version="1.0.0",
        defaultInputModes=["application/json"],
        defaultOutputModes=["application/json"],
    ),
)
