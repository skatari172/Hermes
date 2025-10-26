# backend/services/db_service.py
from services.firebase_client import db
from google.cloud import firestore
from datetime import datetime, date
from typing import Optional, Dict, List
import asyncio
import inspect


def _extract_text_from_gemini_result(result) -> Optional[str]:
    """Robustly extract text from a Gemini-like response object.

    Handles several shapes:
    - plain string
    - dict with 'text' or 'parts' or 'candidates' -> content -> parts
    - objects with attributes .text, .parts, or .candidates
    """
    try:
        if result is None:
            return None
        # Plain string
        if isinstance(result, str):
            return result

        # Dict-like
        if isinstance(result, dict):
            if 'text' in result and isinstance(result['text'], str):
                return result['text']
            # parts at top level
            parts = None
            if 'parts' in result:
                parts = result.get('parts')
            elif 'candidates' in result and isinstance(result['candidates'], list) and result['candidates']:
                cand = result['candidates'][0]
                if isinstance(cand, dict) and 'content' in cand and isinstance(cand['content'], dict) and 'parts' in cand['content']:
                    parts = cand['content']['parts']

            if parts:
                texts = []
                for p in parts:
                    if isinstance(p, str):
                        texts.append(p)
                    elif isinstance(p, dict):
                        if 'text' in p and isinstance(p['text'], str):
                            texts.append(p['text'])
                        elif 'content' in p:
                            c = p['content']
                            if isinstance(c, str):
                                texts.append(c)
                            elif isinstance(c, dict) and 'text' in c:
                                texts.append(c['text'])
                return '\n'.join(texts).strip() if texts else None

        # Object-like with attributes
        # Try .text
        if hasattr(result, 'text') and isinstance(getattr(result, 'text'), str):
            return getattr(result, 'text')

        # Try .parts
        if hasattr(result, 'parts'):
            parts = getattr(result, 'parts')
            texts = []
            for p in parts:
                if isinstance(p, str):
                    texts.append(p)
                elif hasattr(p, 'text'):
                    texts.append(getattr(p, 'text'))
                elif isinstance(p, dict) and 'text' in p:
                    texts.append(p['text'])
            return '\n'.join(texts).strip() if texts else None

        # Try .candidates[0].content.parts
        if hasattr(result, 'candidates'):
            cands = getattr(result, 'candidates')
            if cands:
                first = cands[0]
                # candidate may be object or dict
                if hasattr(first, 'content') and hasattr(first.content, 'parts'):
                    parts = first.content.parts
                    texts = []
                    for p in parts:
                        if isinstance(p, str):
                            texts.append(p)
                        elif hasattr(p, 'text'):
                            texts.append(getattr(p, 'text'))
                    return '\n'.join(texts).strip() if texts else None

    except Exception:
        return None

    return None

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

    # Normalize different storage shapes into a date -> [conversations] map
    date_map: Dict[str, List[dict]] = {}

    for k, v in doc_data.items():
        # Skip non-list values like summaries or other metadata
        if k == 'summaries':
            continue
        if k == 'conversation' and isinstance(v, list):
            # Aggregate entries from the legacy 'conversation' array by their timestamp date
            for conv in v:
                ts = conv.get('timestamp', '')
                if not ts:
                    continue
                d = ts.split('T')[0]
                date_map.setdefault(d, []).append(conv)
        elif isinstance(v, list):
            # New date-keyed list format: key is the date
            date_map.setdefault(k, []).extend(v)

    # Process each date to create one location per day
    for date_key, conversations in date_map.items():
        # Find conversations with location data for this date
        conversations_with_location = []
        for conv in conversations:
            # Check top-level latitude/longitude
            if conv.get("latitude") and conv.get("longitude"):
                conversations_with_location.append(conv)
            # Check nested coordinates.lat/lng
            elif conv.get("coordinates") and conv["coordinates"].get("lat") and conv["coordinates"].get("lng"):
                conversations_with_location.append(conv)

        if not conversations_with_location:
            # No location-bearing conversations for this date -> skip
            continue

        # Use the first conversation's location as the day's location
        first_conv = conversations_with_location[0]

        # Extract latitude and longitude (support both formats)
        if first_conv.get("latitude") and first_conv.get("longitude"):
            latitude = first_conv["latitude"]
            longitude = first_conv["longitude"]
        else:
            # Nested coordinates format
            latitude = first_conv["coordinates"]["lat"]
            longitude = first_conv["coordinates"]["lng"]

        # Combine all messages from the day
        all_messages = [conv.get("message", "") for conv in conversations]
        all_responses = [conv.get("response", "") for conv in conversations]

        # Check if any conversation has a photo (support multiple keys)
        photo_url = None
        for conv in conversations:
            if conv.get("photo_url"):
                photo_url = conv.get("photo_url")
                break
            if conv.get("photoUrl"):
                photo_url = conv.get("photoUrl")
                break
            # permissive: any key containing 'photo'
            for key in conv.keys():
                if 'photo' in key.lower() and conv.get(key):
                    photo_url = conv.get(key)
                    break
            if photo_url:
                break

        # Prefer a generated daily summary from the `entries` collection, if available.
        response_text = f"Multiple conversations from {date_key}"
        try:
            entries_doc = db.collection('entries').document(uid).get()
            if entries_doc.exists:
                entries_data = entries_doc.to_dict() or {}
                summaries = entries_data.get('summaries', {}) if isinstance(entries_data.get('summaries', {}), dict) else {}
                daily_summary = summaries.get(date_key)
                if daily_summary:
                    response_text = daily_summary
        except Exception:
            # If any error reading entries collection, fall back to generic text
            pass

        # Only include a location if we have some meaningful metadata: either a photo
        # or a non-generic daily summary or at least one non-empty response/summary
        has_non_empty_text = any((conv.get('response') or conv.get('summary')) for conv in conversations)
        if not photo_url and response_text.startswith('Multiple conversations') and not has_non_empty_text:
            # No useful media or textual metadata for this date, skip creating a pin
            continue

        locations.append({
            "id": f"daily_{date_key}",
            "latitude": latitude,
            "longitude": longitude,
            "location_name": first_conv.get("location_name", "Unknown Location"),
            "message": f"Day's conversations ({len(conversations)} messages)",
            "response": response_text,
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


def save_entry(uid: str, entry: dict):
    """
    Save a journal entry into a separate `entries` collection organized by user UID.

    Structure:
    - Collection: entries
    - Document: <uid>
    - Fields: date-keyed maps where each date is a map of timestamp_key -> entry
      e.g. { '2025-10-26': { '2025-10-26T12_34_56': { ...entry... } }, 'summaries': { '2025-10-26': 'Diary text' } }

    This function schedules an asynchronous summary regeneration for the affected date.
    """
    try:
        from services.firebase_client import db

        ts = entry.get('timestamp') or datetime.utcnow().isoformat()
        date_key = ts.split('T')[0]
        # Use a safe map key for timestamp (replace ':' with '_') so it can be used as a field name
        ts_key = ts.replace(':', '_')

        doc_ref = db.collection('entries').document(uid)

        # Try to update using dot-path. If doc doesn't exist, set with merge.
        try:
            doc_ref.update({f"{date_key}.{ts_key}": entry})
        except Exception:
            # Create or merge
            doc_ref.set({date_key: {ts_key: entry}}, merge=True)

        # Schedule summary generation for this date in the background
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(generate_and_update_summary(uid, date_key))
        except RuntimeError:
            # No running loop, create a new task
            try:
                asyncio.create_task(generate_and_update_summary(uid, date_key))
            except Exception as e:
                print(f"⚠️ Could not schedule summary generation task: {e}")

    except Exception as e:
        print(f"❌ save_entry error for user {uid}: {e}")


async def generate_and_update_summary(uid: str, date_key: str):
    """
    Generate a single daily diary summary for the given user's date and save it under
    the `summaries` map in the entries/<uid> document. This aggregates all responses
    for the date and stores one central diary string.
    """
    try:
        from utils.gemini_client import gemini_client
        from services.firebase_client import db

        doc_ref = db.collection('entries').document(uid)
        doc = doc_ref.get()
        if not doc.exists:
            print(f"ℹ️ No entries document for user {uid}, skipping summary generation for {date_key}")
            return

        data = doc.to_dict()
        date_map = data.get(date_key, {}) if data else {}

        if not date_map:
            print(f"ℹ️ No entries for {date_key} for user {uid}")
            return

        # Collect recent summaries/responses for the date
        entries = list(date_map.values())
        # Prefer 'summary' or 'response' or 'diary' fields from each entry
        entry_texts = []
        for e in entries:
            text = e.get('diary') or e.get('summary') or e.get('response') or ''
            if text and isinstance(text, str):
                entry_texts.append(text)

        if not entry_texts:
            print(f"ℹ️ No textual content to summarize for {uid} on {date_key}")
            return

        # Build prompt and call LLM
        prompt = (
            f"""Transform the following day's conversation excerpts into a single personal, reflective diary entry (2-3 paragraphs) in first person. Combine the content into a cohesive daily summary.

CRITICAL: Do NOT use coordinates, latitude/longitude, GPS data, or location metadata. Use only the textual content listed below.

Conversation pieces:\n\n{chr(10).join(entry_texts)}"""
        )

        try:
            if inspect.iscoroutinefunction(gemini_client.generate_text):
                gen_result = await gemini_client.generate_text(prompt)
            else:
                gen_result = gemini_client.generate_text(prompt)

            diary_text = _extract_text_from_gemini_result(gen_result)

            if not diary_text:
                print(f"⚠️ Gemini returned empty diary for user {uid} date {date_key}")
                return
        except Exception as gen_err:
            print(f"⚠️ Diary generation failed for user {uid} date {date_key}: {gen_err}")
            return

        # Save diary under summaries map
        try:
            doc_ref.update({f"summaries.{date_key}": diary_text})
            print(f"✅ Saved daily summary for user {uid} date {date_key}")
        except Exception as save_err:
            try:
                # If update failed because summaries doesn't exist yet, merge set
                doc_ref.set({"summaries": {date_key: diary_text}}, merge=True)
                print(f"✅ Created summaries map and saved daily summary for user {uid} date {date_key}")
            except Exception as e:
                print(f"⚠️ Failed to save daily summary for user {uid} date {date_key}: {e}")

    except Exception as e:
        print(f"⚠️ Unexpected error in generate_and_update_summary for {uid} date {date_key}: {e}")


def get_entries_for_date(uid: str, date_key: str) -> dict:
    """
    Retrieve entries for a user on a given date from the `entries` collection.
    Returns a dict: { 'entries': [ ... ], 'summary': str|None, 'images': [ ... ] }
    """
    try:
        from services.firebase_client import db

        doc_ref = db.collection('entries').document(uid)
        doc = doc_ref.get()
        if not doc.exists:
            return {"entries": [], "summary": None, "images": []}

        data = doc.to_dict()
        date_map = data.get(date_key, {}) if data else {}

        # Entries are stored as a map of timestamp_key -> entry
        entries = [v for k, v in date_map.items()] if isinstance(date_map, dict) else []

        # Sort entries by timestamp descending if present
        entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Collect image URLs
        images = []
        for e in entries:
            img = e.get('photo_url') or e.get('photoUrl') or e.get('photo')
            if img:
                images.append(img)

        summary = None
        summaries_map = data.get('summaries', {}) if data else {}
        if summaries_map and isinstance(summaries_map, dict):
            summary = summaries_map.get(date_key)

        return {"entries": entries, "summary": summary, "images": images}

    except Exception as e:
        print(f"❌ get_entries_for_date error for user {uid} date {date_key}: {e}")
        return {"entries": [], "summary": None, "images": []}


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
        prompt = f"""Transform this conversation summary into a personal, reflective diary entry.\n\nCRITICAL: Do NOT reference or use coordinates, GPS data, or any location metadata. Base the diary only on the textual conversation summary provided below.\n\nWrite in first person, introspective and emotionally aware, in 2–3 paragraphs.\nInclude insights, feelings, or reflections on what was learned or experienced.\n\nConversation Summary: {conversation_summary}"""

        # Call gemini_client.generate_text() - support sync or async implementations
        try:
            if inspect.iscoroutinefunction(gemini_client.generate_text):
                gen_result = await gemini_client.generate_text(prompt)
            else:
                gen_result = gemini_client.generate_text(prompt)

            diary_text = _extract_text_from_gemini_result(gen_result)

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
