# backend/routes/journal_routes.py
from fastapi import APIRouter, Depends, Header, HTTPException
from datetime import datetime, date
from utils.auth_util import verify_firebase_token
from services.db_service import save_journal_entry, get_journal_entries
from models.journal import JournalEntryRequest
from config.logger import get_logger
from services.db_service import save_journal_entry, get_journal_entries, get_daily_conversations, save_conversation_entry, get_conversation_locations, get_journal_entries_by_date
from models.journal import JournalEntryRequest, ConversationEntry
from firebase_admin import auth
from typing import Optional
import uuid

router = APIRouter(prefix="/journal", tags=["Journal"])
logger = get_logger(__name__)

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

@router.get("/entries")
def get_journal_entries_by_date_endpoint(uid: str = Depends(verify_firebase_token)):
    """Get journal entries organized by date from journal collection"""
    entries = get_journal_entries_by_date(uid)
    return entries

@router.get("/history")
def get_user_journal(uid: str = Depends(verify_firebase_token)):
    """
    Get user journal history with debug information.
    """
    try:
        logger.info(f"📖 [get_user_journal] Called for user_id={uid}")
        
        # Get journal entries
        journal_data = get_journal_entries(uid)
        
        # Add debug information
        entries = journal_data.get("conversation", [])  # Use "conversation" key
        logger.info(f"Retrieved {len(entries)} journal entries for user {uid}")
        
        # Print debug info to terminal
        print("\n" + "="*80)
        print("📖 JOURNAL HISTORY DEBUG")
        print("="*80)
        print(f"User ID: {uid}")
        print(f"Total entries: {len(entries)}")
        print("-"*80)
        
        for i, entry in enumerate(entries[-3:]):  # Show last 3 entries
            print(f"Entry {i+1}:")
            print(f"  Type: {entry.get('entry_type', 'Unknown')}")
            print(f"  Timestamp: {entry.get('timestamp', 'Unknown')}")
            print(f"  Summary: {entry.get('summary', 'No summary')[:100]}...")
            print("-"*80)
        
        print("="*80 + "\n")
        
        return journal_data
        
    except Exception as e:
        logger.error(f"❌ Error in get_user_journal: {e}", exc_info=True)
        return {"error": str(e), "entries": []}

@router.post("/generate-latest")
async def generate_latest_journal(uid: str = Depends(verify_firebase_token)):
    """
    Generate a journal entry from the latest conversation summary.
    """
    try:
        logger.info(f"📝 [generate_latest_journal] Called for user_id={uid}")
        
        from utils.gemini_client import gemini_client
        from datetime import datetime
        
        # Use a default session_id for now
        session_id = "default_session"
        
        # First, get the journal history to find conversation summaries
        print("\n" + "="*80)
        print("🔍 FETCHING JOURNAL HISTORY FOR CONVERSATION SUMMARY")
        print("="*80)
        print(f"User ID: {uid}")
        print("="*80 + "\n")
        
        # Initialize conversation_summary
        conversation_summary = None
        
        # Get journal history to find conversation summaries
        # Get data directly from journal collection
        journal_history = get_journal_entries(uid)
        
        # Try both keys since there might be inconsistency
        conversations = journal_history.get("conversations", []) or journal_history.get("conversation", [])
        
        print(f"Found {len(conversations)} conversations in journal history")
        print(f"Journal data keys: {list(journal_history.keys())}")
        for i, conv in enumerate(conversations):
            print(f"Conversation {i}: {conv.get('summary', 'No summary')[:50]}...")
        
        # If we didn't get conversation summary from conversations endpoint, try journal history
        if not conversation_summary:
            # Look for conversation summaries in the journal entries
            for entry in reversed(conversations):  # Start from most recent
                if entry.get("summary"):
                    # Check if this entry already has a diary entry
                    if entry.get("diary"):
                        print(f"Entry already has diary entry, skipping: {entry.get('timestamp', 'Unknown time')}")
                        continue
                    conversation_summary = entry.get("summary", "")
                    print(f"Found conversation summary from entry: {entry.get('timestamp', 'Unknown time')}")
                    break
            
            # If no conversation summary found in journal entries, try to create one from recent entries
            if not conversation_summary:
                # Look for any recent entries that might contain conversation data
                recent_entries = conversations[-5:] if len(conversations) >= 5 else conversations
                if recent_entries:
                    # Combine recent entries to create a summary (skip entries that already have diary)
                    entry_summaries = []
                    for entry in recent_entries:
                        if entry.get("summary") and not entry.get("diary"):
                            entry_summaries.append(entry.get("summary"))
                    
                    if entry_summaries:
                        conversation_summary = " | ".join(entry_summaries)
                        print(f"Created conversation summary from {len(entry_summaries)} recent entries (skipped entries with existing diary)")
        
        if not conversation_summary:
            print("\n" + "="*80)
            print("⚠️  NO CONVERSATION SUMMARY AVAILABLE")
            print("="*80)
            print("No conversation summary found in journal history.")
            print("Please have a conversation first before generating a journal entry.")
            print("="*80 + "\n")
            
            return {
                "success": False,
                "message": "No conversation summary available. Please have a conversation first before generating a journal entry."
            }
        
        # Display the summary and generate journal entry
        print("\n" + "="*80)
        print("🚀 TRIGGERING JOURNAL GENERATION FROM CONVERSATION")
        print("="*80)
        print(f"User ID: {uid}")
        print(f"Session ID: {session_id}")
        print(f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        
        # Display the summary prominently in the terminal
        print("\n" + "="*80)
        print("📋 CONVERSATION SUMMARY FOR JOURNAL GENERATION")
        print("="*80)
        print(f"User ID: {uid}")
        print(f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*80)
        print("SUMMARY:")
        print(conversation_summary)
        print("-"*80)
        print("🔄 Generating journal entry...")
        print("="*80 + "\n")
        
        # Build simple prompt for Gemini - only use the conversation summary
        prompt = f"""Transform this conversation summary into a personal, reflective diary entry.

Write in first person, introspective and emotionally aware, in 2–3 paragraphs.
Include insights, feelings, or reflections on what was learned or experienced.

Conversation Summary: {conversation_summary}"""

        logger.debug(f"Prompt sent to Gemini:\n{prompt}\n")

        # Generate journal-style text
        diary_text = gemini_client.generate_text(prompt)
        logger.info("✅ Gemini response received successfully.")
        logger.debug(f"Generated diary entry:\n{diary_text}\n")

        # Display the generated journal entry in terminal
        print("\n" + "="*80)
        print("📖 GENERATED JOURNAL ENTRY")
        print("="*80)
        print(diary_text)
        print("="*80 + "\n")

        # Find the conversation entry that we used for the summary and add diary field to it
        conversation_entry_updated = False
        for entry in conversations:
            if entry.get("summary") == conversation_summary:
                # Update the existing entry with diary field
                entry["diary"] = diary_text
                conversation_entry_updated = True
                print(f"✅ Updated existing conversation entry with diary field")
                print(f"Entry now has: photoUrl, summary, timestamp, diary")
                break
        
        if conversation_entry_updated:
            # Save the updated conversations back to the database
            try:
                from services.firebase_client import db
                
                # Update the entire conversation array with the modified entry
                doc_ref = db.collection("journal").document(uid)
                doc_ref.set({
                    "conversation": conversations
                }, merge=False)  # Replace the entire array
                print(f"✅ Updated journal document with diary field for user {uid}")
            except Exception as e:
                print(f"⚠️ Could not update journal document in database: {e}")
                print(f"Error details: {str(e)}")
        else:
            print(f"⚠️ Could not find matching conversation entry to update")
            print(f"Available summaries: {[entry.get('summary', 'No summary') for entry in conversations]}")

        return {
            "success": True,
            "message": "Journal entry generated successfully",
            "diary_entry": diary_text,
            "timestamp": datetime.utcnow().isoformat()
        }
            
    except Exception as e:
        logger.error(f"❌ Error in generate_latest_journal: {e}", exc_info=True)
        print(f"❌ Error creating journal entry: {e}")
        return {
            "success": False,
            "message": f"Error generating journal entry: {str(e)}"
        }
