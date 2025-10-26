# backend/routes/chat_routes.py
from fastapi import APIRouter, Form, HTTPException, Depends
from utils.auth_util import verify_firebase_token
from datetime import datetime
import json
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# In-memory session storage for chat conversations
chat_sessions = {}

@router.post("/")
async def chat_with_context(
    user_message: str = Form(...),
    user_id: str = Depends(verify_firebase_token),
    session_id: str = Form(default="demo_session")
):
    """Handle chat messages with conversation context and in-memory session storage."""
    try:
        print(f"💬 Chat request from {user_id}: {user_message[:50]}...")
        
        # Get or create session in memory
        session_key = f"{user_id}_{session_id}"
        if session_key not in chat_sessions:
            chat_sessions[session_key] = {
                "user_id": user_id,
                "session_id": session_id,
                "conversation_history": [],
                "context_data": None,
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat()
            }
            print(f"📝 Created new chat session: {session_key}")
        
        # Update last activity
        chat_sessions[session_key]["last_activity"] = datetime.utcnow().isoformat()
        
        # Get previous context from session or database
        session_data = chat_sessions[session_key]
        previous_context = session_data.get("context_data")
        
        if not previous_context:
            # Try to get context from database if not in memory
            previous_context = await get_conversation_context(user_id, session_id)
            if previous_context.get("success"):
                session_data["context_data"] = previous_context
        
        # Add conversation history to context
        conversation_history = session_data.get("conversation_history", [])
        if previous_context:
            previous_context["conversation_history"] = conversation_history
        else:
            previous_context = {"conversation_history": conversation_history}
        
        # Generate response using context
        from utils.response_utils import generate_cultural_response_with_context
        
        response_result = await generate_cultural_response_with_context(
            user_message=user_message,
            context_data=previous_context or {},
            user_id=user_id,
            session_id=session_id
        )
        
        # Store conversation turn in memory
        conversation_turn = {
            "role": "user",
            "message": user_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        session_data["conversation_history"].append(conversation_turn)
        
        conversation_turn = {
            "role": "assistant", 
            "message": response_result.get("response", ""),
            "timestamp": datetime.utcnow().isoformat()
        }
        session_data["conversation_history"].append(conversation_turn)
        
        # Store conversation in database as well
        await store_conversation_turn(user_id, session_id, user_message, response_result.get("response", ""))
        
        print(f"✅ Chat response generated and stored in session")
        
        return {
            "status": "success",
            "response": response_result.get("response", "I apologize, but I couldn't generate a response."),
            "user_message": user_message,
            "context_used": response_result.get("context_used", {}),
            "metadata": response_result.get("metadata", {}),
            "session_info": {
                "session_id": session_id,
                "conversation_length": len(session_data["conversation_history"]),
                "has_context": bool(session_data.get("context_data"))
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return {
            "status": "error",
            "message": f"Chat processing failed: {str(e)}",
            "response": "I apologize, but I'm having trouble processing your message right now."
        }

@router.get("/session/{user_id}/{session_id}")
async def get_session_info(user_id: str, session_id: str):
    """Get chat session information."""
    try:
        session_key = f"{user_id}_{session_id}"
        
        if session_key in chat_sessions:
            session_data = chat_sessions[session_key]
            return {
                "status": "success",
                "session_info": {
                    "user_id": session_data["user_id"],
                    "session_id": session_data["session_id"],
                    "conversation_length": len(session_data["conversation_history"]),
                    "has_context": bool(session_data.get("context_data")),
                    "created_at": session_data["created_at"],
                    "last_activity": session_data["last_activity"],
                    "context_entity": session_data.get("context_data", {}).get("entity", "None") if session_data.get("context_data") else "None"
                }
            }
        else:
            return {
                "status": "not_found",
                "message": "Session not found"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get session info: {str(e)}"
        }

# Helper functions (these would be imported from main.py or a shared module)
async def get_conversation_context(user_id: str, session_id: str) -> dict:
    """Get previous conversation context from database."""
    try:
        # TODO: Replace with actual database query
        # For now, return mock context
        return {
            "success": True,
            "entity": "Previous Cultural Site",
            "entity_type": "cultural_site",
            "verified": True,
            "certainty": 0.8,
            "cultural_summary": "Previous conversation about cultural sites and landmarks",
            "coordinates": {"lat": 28.5436, "lng": -81.3738},
            "conversation_history": [
                {"role": "user", "message": "Tell me about this place"},
                {"role": "assistant", "message": "This is a fascinating cultural site..."}
            ]
        }
    except Exception as e:
        print(f"❌ Context retrieval error: {e}")
        return {
            "success": False,
            "error": str(e),
            "entity": "Unknown Entity",
            "cultural_summary": "No previous context available"
        }

async def store_conversation_turn(user_id: str, session_id: str, user_message: str, assistant_response: str) -> dict:
    """Store conversation turn in database."""
    try:
        print(f"💾 Storing conversation turn for {user_id}...")
        
        conversation_data = {
            "user_id": user_id,
            "session_id": session_id,
            "user_message": user_message,
            "assistant_response": assistant_response,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # TODO: Replace with actual database call
        print(f"📝 Would store conversation: {json.dumps(conversation_data, indent=2)}")
        
        return {
            "success": True,
            "message": "Conversation stored successfully"
        }
        
    except Exception as e:
        print(f"❌ Conversation storage error: {e}")
        return {
            "success": False,
            "error": str(e)
        }