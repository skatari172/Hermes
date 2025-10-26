# backend/services/db_service.py
from services.firebase_client import db
from google.cloud import firestore
from datetime import datetime, date
from typing import Optional, Dict, List
import asyncio
import inspect

def save_cultural_summary(user_id: str, session_id: str, cultural_data: dict):
    """
    Saves cultural summary data to Firestore for a specific user session.
    """
    doc_ref = db.collection("cultural_summaries").document(f"{user_id}_{session_id}")
    
    # Set the document with the cultural data
    doc_ref.set(cultural_data, merge=True)


def get_cultural_summary(user_id: str, session_id: str):
    """
    Retrieves cultural summary data for a specific user session.
    """
    doc_ref = db.collection("cultural_summaries").document(f"{user_id}_{session_id}")
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None


def save_journal_entry(uid: str, entry: dict):
    """
    Adds a chat summary (photo + summary + timestamp) to the user's Firestore document.
    """
    doc_ref = db.collection("journal").document(uid)

    # If the doc doesn't exist yet, create it with the first entry
    doc = doc_ref.get()
    if not doc.exists:
        doc_ref.set({"conversation": [entry]})
    else:
        # Append entry to conversation array
        doc_ref.update({
            "conversation": firestore.ArrayUnion([entry])
        })

def save_conversation_entry(uid: str, entry: dict):
    """
    Save a conversation entry organized by date.
    Creates a new document for each unique user ID.
    """
    print(f"💾 Saving conversation for user: {uid}")
    print(f"📝 Entry data: {entry}")
    
    # Get current date for organization
    entry_date = datetime.fromisoformat(entry["timestamp"]).date().isoformat()
    print(f"📅 Entry date: {entry_date}")
    
    # Store conversations inside the `journal` collection to consolidate chat + journal data
    doc_ref = db.collection("journal").document(uid)
    
    # Get existing document
    doc = doc_ref.get()
    
    if not doc.exists:
        # Create new document with first entry
        print(f"🆕 Creating new conversation document for user: {uid}")
        doc_ref.set({
            entry_date: [entry]
        })
        print(f"✅ Created new document with first entry for {entry_date}")
    else:
        print(f"📋 Document exists for user: {uid}")
        doc_data = doc.to_dict()
        if entry_date in doc_data:
            # Update existing date's entries
            print(f"📝 Adding to existing date {entry_date}")
            doc_ref.update({
                entry_date: firestore.ArrayUnion([entry])
            })
        else:
            # Add new date
            print(f"🆕 Adding new date {entry_date}")
            doc_ref.update({
                entry_date: [entry]
            })
    
    print(f"✅ Successfully saved conversation entry for user {uid} on {entry_date}")

    # After saving a conversation entry, asynchronously attempt to generate a diary
    # entry for the user's journal. This runs in the background so the request
    # that triggered the save does not block on LLM generation.
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(generate_and_save_diary_for_user(uid))
    except RuntimeError:
        # No running loop (e.g., invoked outside async context) - schedule via asyncio
        try:
            asyncio.create_task(generate_and_save_diary_for_user(uid))
        except Exception as e:
            print(f"⚠️ Could not schedule diary generation task: {e}")

def get_daily_conversations(uid: str, date_filter: Optional[str] = None) -> Dict:
    """
    Get conversations organized by date. Reads from the `journal` collection where
    conversations are now stored (date-keyed). Returns the same structure as before.
    """
    doc_ref = db.collection("journal").document(uid)
    doc = doc_ref.get()
    
    if not doc.exists:
        return {"conversations": {}}
    
    doc_data = doc.to_dict()
    
    if date_filter:
        # Return only conversations for specific date
        return {
            "conversations": {
                date_filter: doc_data.get(date_filter, [])
            }
        }
    
    # Return all conversations organized by date
    return {"conversations": doc_data}

def get_conversation_locations(uid: str) -> List[Dict]:
    """
    Get daily conversation locations for map display.
    Returns one location per day with all conversations for that day grouped together.
    """
    # Conversation locations are derived from the date-keyed conversation structure
    # stored under the `journal` collection for each user.
    doc_ref = db.collection("journal").document(uid)
    doc = doc_ref.get()
    
    if not doc.exists:
        return []
    
    doc_data = doc.to_dict()
    locations = []
    
    # Process each date to create one location per day
    for date_key, conversations in doc_data.items():
        # Find conversations with location data for this date
        conversations_with_location = [
            conv for conv in conversations 
            if conv.get("latitude") and conv.get("longitude")
        ]
        
        if conversations_with_location:
            # Use the first conversation's location as the day's location
            # (You could also calculate an average if multiple locations per day)
            first_conv = conversations_with_location[0]
            
            # Combine all messages from the day
            all_messages = [conv.get("message", "") for conv in conversations]
            all_responses = [conv.get("response", "") for conv in conversations]
            
            # Check if any conversation has a photo
            photo_url = None
            for conv in conversations:
                if conv.get("photo_url"):
                    photo_url = conv.get("photo_url")
                    break
            
            locations.append({
                "id": f"daily_{date_key}",
                "latitude": first_conv["latitude"],
                "longitude": first_conv["longitude"],
                "location_name": first_conv.get("location_name", "Unknown Location"),
                "message": f"Day's conversations ({len(conversations)} messages)",
                "response": f"Multiple conversations from {date_key}",
                "photo_url": photo_url,
                "timestamp": first_conv.get("timestamp", ""),
                "date": date_key,
                "total_conversations": len(conversations),
                "all_messages": all_messages,
                "all_responses": all_responses,
                "conversations": conversations  # Include all conversations for the day
            })
    
    # Sort by date (newest first)
    locations.sort(key=lambda x: x["date"], reverse=True)
    return locations

def get_journal_entries(uid: str):
    """
    Retrieves all conversation summaries for a user.
    """
    doc_ref = db.collection("journal").document(uid)
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else {"conversation": []}

def get_journal_entries_by_date(uid: str) -> Dict:
    """
    Get journal entries organized by date from the journal collection.
    """
    doc_ref = db.collection("journal").document(uid)
    doc = doc_ref.get()
    
    if not doc.exists:
        return {"journal_entries": {}}
    
    doc_data = doc.to_dict()
    journal_entries = doc_data.get("conversation", [])
    
    # Group by date
    entries_by_date = {}
    for entry in journal_entries:
        timestamp = entry.get("timestamp", "")
        if timestamp:
            # Extract date from timestamp
            entry_date = timestamp.split("T")[0]  # Gets YYYY-MM-DD
            if entry_date not in entries_by_date:
                entries_by_date[entry_date] = []
            entries_by_date[entry_date].append(entry)
    
    # Sort entries within each date by timestamp (newest first)
    for date_key in entries_by_date:
        entries_by_date[date_key].sort(
            key=lambda x: x.get("timestamp", ""), 
            reverse=True
        )
    
    return {"journal_entries": entries_by_date}

def update_journal_entry(uid: str, timestamp: str, summary: str, diary: Optional[str] = None) -> bool:
    """
    Update a journal entry by timestamp.
    """
    doc_ref = db.collection("journal").document(uid)
    doc = doc_ref.get()
    
    if not doc.exists:
        return False
    
    doc_data = doc.to_dict()
    journal_entries = doc_data.get("conversation", [])
    
    # Find the entry with matching timestamp
    updated = False
    for entry in journal_entries:
        if entry.get("timestamp") == timestamp:
            entry["summary"] = summary
            if diary is not None:
                entry["diary"] = diary
            updated = True
            break
    
    if updated:
        # Update the entire conversation array
        doc_ref.update({"conversation": journal_entries})
        return True
    
    return False


async def generate_and_save_diary_for_user(uid: str):
    """
    Generate a diary entry from the user's recent conversations and save it
    into the matching conversation entry's `diary` field inside the user's
    `journal` document.

    This function is resilient to different conversation storage shapes:
    - date-keyed lists (e.g., { '2025-10-26': [entries] })
    - a top-level 'conversation' array
    """
    try:
        from utils.gemini_client import gemini_client
        from services.firebase_client import db

        doc_ref = db.collection('journal').document(uid)
        doc = doc_ref.get()
        if not doc.exists:
            print(f"ℹ️ No journal document for user {uid}, skipping diary generation")
            return

        doc_data = doc.to_dict()

        # Flatten conversation entries from possible layouts
        conversations = []
        # If there's a 'conversation' array, use it
        if isinstance(doc_data.get('conversation'), list):
            conversations = doc_data.get('conversation', [])
        else:
            # Otherwise, gather all list-typed values (date-keyed)
            for k, v in doc_data.items():
                if isinstance(v, list):
                    conversations.extend(v)

        if not conversations:
            print(f"ℹ️ No conversations to summarize for user {uid}")
            return

        # Try to find an existing summary that doesn't yet have a diary
        conversation_summary = None
        target_timestamp = None
        for entry in reversed(conversations):
            if entry.get('summary') and not entry.get('diary'):
                conversation_summary = entry.get('summary')
                target_timestamp = entry.get('timestamp')
                break

        # If none found, create one from recent responses/summaries
        if not conversation_summary:
            recent_entries = conversations[-5:] if len(conversations) >= 5 else conversations
            entry_summaries = []
            for entry in recent_entries:
                if entry.get('summary') and not entry.get('diary'):
                    entry_summaries.append(entry.get('summary'))

            if entry_summaries:
                conversation_summary = ' | '.join(entry_summaries)
                target_timestamp = recent_entries[-1].get('timestamp')

        if not conversation_summary:
            print(f"ℹ️ Could not build a conversation summary for user {uid}")
            return

        # Build prompt for LLM
        prompt = f"""Transform this conversation summary into a personal, reflective diary entry.

Write in first person, introspective and emotionally aware, in 2–3 paragraphs.
Include insights, feelings, or reflections on what was learned or experienced.

CRITICAL REQUIREMENTS:
1. NEVER mention coordinates, latitude, longitude, or GPS data
2. NO asterisks (*), NO bold formatting, NO markdown whatsoever
3. Write naturally and personally, plain text only
4. Keep it concise and meaningful

Conversation Summary: {conversation_summary}"""

        # Call gemini_client.generate_text() - support sync or async implementations
        try:
            diary_text = None
            if inspect.iscoroutinefunction(gemini_client.generate_text):
                diary_text = await gemini_client.generate_text(prompt)
            else:
                diary_text = gemini_client.generate_text(prompt)

            if not diary_text:
                print(f"⚠️ Gemini returned empty diary for user {uid}")
                return
        except Exception as gen_err:
            print(f"⚠️ Diary generation failed for user {uid}: {gen_err}")
            return

        # Find the matching conversation entry and set diary field
        updated = False
        # If doc_data has 'conversation' array, update in-place
        if isinstance(doc_data.get('conversation'), list):
            for entry in doc_data['conversation']:
                if entry.get('timestamp') == target_timestamp:
                    entry['diary'] = diary_text
                    updated = True
                    break
        else:
            # Search date-keyed lists
            for date_key, convs in list(doc_data.items()):
                if isinstance(convs, list):
                    for idx, entry in enumerate(convs):
                        if entry.get('timestamp') == target_timestamp:
                            doc_data[date_key][idx]['diary'] = diary_text
                            updated = True
                            break
                    if updated:
                        break

        if updated:
            try:
                # Overwrite the document with the updated structure
                doc_ref.set(doc_data, merge=False)
                print(f"✅ Diary saved for user {uid} (timestamp={target_timestamp})")
            except Exception as save_err:
                print(f"⚠️ Failed to save diary for user {uid}: {save_err}")
        else:
            print(f"⚠️ Could not find matching conversation entry to attach diary for user {uid}")

    except Exception as e:
        print(f"⚠️ Unexpected error in generate_and_save_diary_for_user for {uid}: {e}")
