# backend/routes/journal_routes.py
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from urllib.parse import urljoin, urlparse
from datetime import datetime, date
from utils.auth_util import verify_firebase_token
from services.db_service import save_journal_entry, get_journal_entries
from fastapi import Request
from models.journal import JournalEntryRequest
from config.logger import get_logger
from services.db_service import save_journal_entry, get_journal_entries, get_daily_conversations, save_conversation_entry, get_conversation_locations, get_journal_entries_by_date, update_journal_entry
from models.journal import JournalEntryRequest, ConversationEntry, JournalEntryUpdate
from services.db_service import save_journal_entry, get_journal_entries, get_daily_conversations, save_conversation_entry, get_conversation_locations, get_journal_entries_by_date
from services.db_service import save_entry, get_entries_for_date
from models.journal import JournalEntryRequest, ConversationEntry
from config.logger import get_logger
from firebase_admin import auth
from typing import Optional
import uuid

router = APIRouter(prefix="/journal", tags=["Journal"])
logger = get_logger(__name__)


def _normalize_photo_url(photo_url: str, request: Request) -> str:
    """Normalize stored photo paths to absolute URLs using the incoming request base URL."""
    try:
        if not photo_url:
            return photo_url
        p = str(photo_url).strip()
        # Treat explicit placeholder markers as missing images
        if 'placeholder_image_url' in p.lower():
            return None
        # If already absolute, return as-is
        if p.startswith('http://') or p.startswith('https://'):
            return p
        # If looks like an uploads or profile local path, join with request.base_url
        if p.startswith('/'):
            p = p.lstrip('/')
        if p.startswith('uploads') or p.startswith('profile'):
            base = str(request.base_url)
            return urljoin(base, p)
        # If it looks like a gs:// or storage url, return as-is
        if 'storage.googleapis.com' in p or p.startswith('gs://'):
            return p
        return photo_url
    except Exception:
        return photo_url

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
    request: Request,
    uid: str = Depends(get_user_id),
    date_filter: Optional[str] = None
):
    """Get user conversations, optionally filtered by date. Normalizes photo URLs to be reachable by the client."""
    print(f"🔍 Getting conversations for user: {uid}")
    conversations = get_daily_conversations(uid, date_filter)

    # Normalize photo URLs in-place
    try:
        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in ("photo_url", "photoUrl") and v:
                        o[k] = _normalize_photo_url(v, request)
                    else:
                        walk(v)
            elif isinstance(o, list):
                for item in o:
                    walk(item)

        walk(conversations)
    except Exception:
        pass

    print(f"📋 Found conversations: {conversations}")
    return conversations

@router.get("/conversations/all")
def get_all_users_conversations(
    request: Request,
    uid: str = Depends(get_user_id),
    limit: int = 50
):
    """Get conversations from all registered users for social feed"""
    print(f"🔍 Getting all users' conversations for social feed (requested by: {uid})")
    
    try:
        from services.firebase_client import db
        from firebase_admin import auth
        
        all_conversations = []
        user_profiles = {}
        
        # Get all documents from the journal collection
        journal_docs = db.collection("journal").stream()
        
        for doc in journal_docs:
            user_id = doc.id
            doc_data = doc.to_dict()
            
            if not doc_data:
                print(f"⚠️ User {user_id} has no data")
                continue
            
            print(f"🔍 Processing user {user_id}, doc_data keys: {list(doc_data.keys())}")
            
            # Get user profile information
            try:
                user_record = auth.get_user(user_id)
                user_profiles[user_id] = {
                    "name": user_record.display_name or "Anonymous User",
                    "username": user_record.email.split("@")[0] if user_record.email else f"user_{user_id[:8]}",
                    "avatar": user_record.photo_url
                }
            except Exception as e:
                print(f"⚠️ Could not get profile for user {user_id}: {e}")
                user_profiles[user_id] = {
                    "name": "Anonymous User",
                    "username": f"user_{user_id[:8]}",
                    "avatar": None
                }
            
            # Check for 'conversation' key (array format) first
            if 'conversation' in doc_data and isinstance(doc_data['conversation'], list):
                print(f"📝 Found conversation array for user {user_id}: {len(doc_data['conversation'])} entries")
                for i, entry in enumerate(doc_data['conversation']):
                    if isinstance(entry, dict):
                        # Add user info and append to all_conversations
                        conversation_with_user = {
                            **entry,
                            'user_id': user_id,
                            'user_profile': user_profiles[user_id]
                        }
                        all_conversations.append(conversation_with_user)
                        print(f"  ✅ Added entry {i+1}: {entry.get('summary', 'No summary')[:50]}...")
                    else:
                        print(f"  ⚠️ Entry {i} is not a dict: {type(entry)}")
            
            # Also check for date-keyed format (fallback for old data structure)
            for key, value in doc_data.items():
                # Skip the 'conversation' key we already processed
                if key == 'conversation':
                    continue
                    
                # Check if this looks like a date key (YYYY-MM-DD format)
                if isinstance(value, list) and '-' in key:
                    print(f"📅 Found date-keyed conversations for user {user_id} on {key}: {len(value)} entries")
                    for i, entry in enumerate(value):
                        if isinstance(entry, dict):
                            conversation_with_user = {
                                **entry,
                                'user_id': user_id,
                                'user_profile': user_profiles[user_id]
                            }
                            all_conversations.append(conversation_with_user)
                            print(f"  ✅ Added entry {i+1} from {key}")
        
        print(f"\n📊 Total conversations collected: {len(all_conversations)}")
        
        # Remove duplicates based on timestamp and user_id
        seen_entries = set()
        unique_conversations = []
        
        for entry in all_conversations:
            # Create a unique key
            timestamp = entry.get('timestamp', '')
            user_id = entry.get('user_id', '')
            message = entry.get('message', '')[:50]  # First 50 chars of message
            
            unique_key = f"{user_id}-{timestamp}-{hash(message)}"
            
            if unique_key not in seen_entries:
                seen_entries.add(unique_key)
                unique_conversations.append(entry)
        
        print(f"📊 Unique conversations after deduplication: {len(unique_conversations)}")
        
        # Sort by timestamp (newest first)
        unique_conversations.sort(
            key=lambda x: x.get('timestamp', ''), 
            reverse=True
        )
        
        # Apply limit
        limited_conversations = unique_conversations[:limit]
        
        print(f"✅ Returning {len(limited_conversations)} conversations from {len(user_profiles)} users\n")
        
        # Normalize any photo URLs in the returned conversations and avatars
        try:
            for entry in limited_conversations:
                # Normalize photo on the conversation entry
                if entry.get('photo_url'):
                    entry['photo_url'] = _normalize_photo_url(entry['photo_url'], request)
                if entry.get('photoUrl'):
                    entry['photoUrl'] = _normalize_photo_url(entry['photoUrl'], request)

                # Normalize user avatar if present in user_profile
                up = entry.get('user_profile')
                if up and up.get('avatar'):
                    up['avatar'] = _normalize_photo_url(up['avatar'], request)
        except Exception:
            pass

        return {
            "conversations": limited_conversations,
            "total_count": len(unique_conversations),
            "user_count": len(user_profiles)
        }
        
    except Exception as e:
        print(f"❌ Error getting all users' conversations: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching conversations: {str(e)}")

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
def get_conversation_locations(request: Request, uid: str = Depends(get_user_id)):
    """Get all conversation locations for map display and normalize photo URLs."""
    from services.db_service import get_conversation_locations
    locations = get_conversation_locations(uid)
    try:
        for loc in locations:
            if loc.get('photo_url'):
                loc['photo_url'] = _normalize_photo_url(loc['photo_url'], request)
            # Also normalize nested conversation photo URLs if present
            if loc.get('conversations') and isinstance(loc.get('conversations'), list):
                for conv in loc['conversations']:
                    if conv.get('photo_url'):
                        conv['photo_url'] = _normalize_photo_url(conv['photo_url'], request)
    except Exception:
        pass

    return {"locations": locations}


@router.get("/daily_entries")
def get_daily_entries(request: Request, uid: str = Depends(verify_firebase_token), date: Optional[str] = None):
    """
    Return per-day centralized entries (summary + images + entries list) from the `entries` collection.
    If `date` is provided, returns only that date; otherwise returns a map of available dates.
    """
    try:
        # If a specific date requested, return only that date
        if date:
            result = get_entries_for_date(uid, date)
            # Normalize any image URLs using request
            try:
                if result.get('images'):
                    result['images'] = [ _normalize_photo_url(u, request) for u in result['images'] if u and not (isinstance(u, str) and 'placeholder_image_url' in u.lower()) ]
                # Normalize image URLs inside entries
                for e in result.get('entries', []):
                    if e.get('photo_url'):
                        e['photo_url'] = _normalize_photo_url(e['photo_url'], request)
            except Exception:
                pass
            return {date: result}

        # No date specified: try to return all dates available for this user
        from services.firebase_client import db
        doc = db.collection('entries').document(uid).get()
        if not doc.exists:
            return {"daily_entries": {}}

        data = doc.to_dict()
        daily = {}
        for k, v in data.items():
            if k == 'summaries':
                continue
            # For each date map, build the entries/summary/images bundle
            bundle = get_entries_for_date(uid, k)
            # Normalize images
            try:
                bundle['images'] = [ _normalize_photo_url(u, request) for u in bundle.get('images', []) if u and not (isinstance(u, str) and 'placeholder_image_url' in u.lower()) ]
                for e in bundle.get('entries', []):
                    if e.get('photo_url'):
                        e['photo_url'] = _normalize_photo_url(e['photo_url'], request)
            except Exception:
                pass
            daily[k] = bundle

        return {"daily_entries": daily}
    except Exception as e:
        return {"error": str(e)}

@router.get("/entries")
def get_journal_entries_by_date_endpoint(request: Request, uid: str = Depends(verify_firebase_token)):
    """Get journal entries organized by date from journal collection and normalize photo URLs."""
    entries = get_journal_entries_by_date(uid)
    try:
        journal_entries = entries.get('journal_entries', {})
        for date_key, arr in journal_entries.items():
            for entry in arr:
                # Some entries use 'photoUrl' key
                if entry.get('photoUrl'):
                    entry['photoUrl'] = _normalize_photo_url(entry['photoUrl'], request)
                if entry.get('photo_url'):
                    entry['photo_url'] = _normalize_photo_url(entry['photo_url'], request)
    except Exception:
        pass
    return entries

# Note: /entries endpoint with Request-aware normalization is defined above.

@router.patch("/entries/{timestamp}")
def update_journal_entry_endpoint(
    timestamp: str,
    update_data: JournalEntryUpdate,
    uid: str = Depends(verify_firebase_token)
):
    """Update a journal entry by timestamp"""
    success = update_journal_entry(uid, timestamp, update_data.summary, update_data.diary)
    if success:
        return {"message": "Journal entry updated successfully", "success": True}
    else:
        raise HTTPException(status_code=404, detail="Journal entry not found")

@router.get("/history")
def get_user_journal(request: Request, uid: str = Depends(verify_firebase_token)):
    """
    Get user journal history with debug information.
    """
    try:
        logger.info(f"📖 [get_user_journal] Called for user_id={uid}")
        
        # Get journal entries
        journal_data = get_journal_entries(uid)

        # Normalize photo URLs in conversation entries if present
        try:
            def walk(o):
                if isinstance(o, dict):
                    for k, v in o.items():
                        if k in ("photo_url", "photoUrl") and v:
                            o[k] = _normalize_photo_url(v, request)
                        else:
                            walk(v)
                elif isinstance(o, list):
                    for item in o:
                        walk(item)
            walk(journal_data)
        except Exception:
            pass
        
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
