# backend/routes/journal_routes.py
from fastapi import APIRouter, Depends, Header, HTTPException
from datetime import datetime, date
from utils.auth_util import verify_firebase_token
from services.db_service import save_journal_entry, get_journal_entries, get_daily_conversations, save_conversation_entry, get_conversation_locations
from models.journal import JournalEntryRequest, ConversationEntry
from firebase_admin import auth
from typing import Optional
import uuid

router = APIRouter(prefix="/journal", tags=["Journal"])

def get_user_id(authorization: str = Header(None)):
    """
    Get user ID from auth token - ONLY Firebase auth, no fallbacks
    """
    if not authorization or not authorization.startswith("Bearer "):
        print(f"❌ No authorization header provided")
        raise HTTPException(status_code=401, detail="No authorization token provided")
    
    token = authorization.split("Bearer ")[1]
    print(f"🔍 Received token: {token[:20]}...{token[-10:] if len(token) > 30 else token}")
    
    # ONLY Firebase auth - no fallbacks
    try:
        decoded_token = auth.verify_id_token(token)
        firebase_uid = decoded_token["uid"]
        print(f"✅ Firebase auth successful for UID: {firebase_uid}")
        return firebase_uid
    except Exception as e:
        print(f"❌ Firebase token verification failed: {str(e)}")
        print(f"❌ Token that failed: {token}")
        raise HTTPException(status_code=401, detail=f"Firebase auth failed: {str(e)}")

@router.post("/add")
def add_journal(
    entry: JournalEntryRequest,
    uid: str = Depends(verify_firebase_token)
):
    data = {
        "photoUrl": entry.photo_url,
        "summary": entry.summary,
        "timestamp": datetime.utcnow().isoformat()
    }

    save_journal_entry(uid, data)
    return {"message": "Journal entry saved successfully"}

@router.post("/conversation")
def add_conversation_entry(
    entry: ConversationEntry,
    uid: str = Depends(get_user_id)
):
    """Add a conversation entry with location and content"""
    data = {
        "message": entry.message,
        "response": entry.response,
        "timestamp": datetime.utcnow().isoformat(),
        "latitude": entry.latitude,
        "longitude": entry.longitude,
        "location_name": entry.location_name,
        "photo_url": entry.photo_url,
        "session_id": entry.session_id
    }

    save_conversation_entry(uid, data)
    return {"message": "Conversation entry saved successfully"}

@router.get("/conversations")
def get_user_conversations(
    uid: str = Depends(get_user_id),
    date_filter: Optional[str] = None
):
    """Get user conversations, optionally filtered by date"""
    print(f"🔍 Getting conversations for user: {uid}")
    conversations = get_daily_conversations(uid, date_filter)
    print(f"📋 Found conversations: {conversations}")
    return conversations

@router.get("/debug/user")
def debug_user_info(uid: str = Depends(get_user_id)):
    """Debug endpoint to check user ID and available conversations"""
    from services.db_service import get_daily_conversations
    conversations = get_daily_conversations(uid)
    
    # Also check if there are any conversations under common user ID patterns
    potential_uids = [uid]
    if not uid.startswith("demo_"):
        potential_uids.extend([f"demo_user_{uid}", f"temp_user_{uid[:8]}"])
    
    all_conversations = {}
    for test_uid in potential_uids:
        test_conversations = get_daily_conversations(test_uid)
        if test_conversations.get("conversations"):
            all_conversations[test_uid] = test_conversations
    
    return {
        "current_user_id": uid,
        "conversations_for_current_user": conversations,
        "all_potential_conversations": all_conversations
    }

@router.post("/debug/test-conversation")
def create_test_conversation(uid: str = Depends(get_user_id)):
    """Create a test conversation for debugging"""
    from datetime import datetime
    
    test_conversation = {
        "message": "This is a test message to verify the conversation system works",
        "response": "This is a test response from Hermes to confirm everything is working correctly.",
        "timestamp": datetime.utcnow().isoformat(),
        "latitude": 37.7749,
        "longitude": -122.4194,
        "location_name": "San Francisco, CA (Test Location)",
        "photo_url": "https://via.placeholder.com/300x200/007AFF/FFFFFF?text=Test+Image",
        "session_id": f"test_session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    }
    
    save_conversation_entry(uid, test_conversation)
    
    return {
        "message": "Test conversation created successfully",
        "user_id": uid,
        "conversation": test_conversation
    }

@router.get("/locations")
def get_conversation_locations(uid: str = Depends(get_user_id)):
    """Get all conversation locations for map display"""
    from services.db_service import get_conversation_locations
    locations = get_conversation_locations(uid)
    return {"locations": locations}

@router.get("/history")
def get_user_journal(uid: str = Depends(verify_firebase_token)):
    return get_journal_entries(uid)
