# backend/services/db_service.py
from services.firebase_client import db
from google.cloud import firestore
from datetime import datetime, date
from typing import Optional, Dict, List

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
    
    doc_ref = db.collection("conversations").document(uid)
    
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

def get_daily_conversations(uid: str, date_filter: Optional[str] = None) -> Dict:
    """
    Get conversations organized by date.
    """
    doc_ref = db.collection("conversations").document(uid)
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
    doc_ref = db.collection("conversations").document(uid)
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
