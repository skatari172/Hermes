"""
Storage Utilities
Functions for storing data in Firebase
"""
from datetime import datetime
import asyncio


async def store_cultural_summary(context_result: dict, user_id: str, session_id: str) -> dict:
    """Store cultural summary in database."""
    try:
        print("💾 Storing cultural summary in database...")
        
        # Prepare data for database
        cultural_data = {
            "user_id": user_id,
            "session_id": session_id,
            "entity": context_result.get("entity", "Unknown"),
            "entity_type": context_result.get("entity_type", "unknown"),
            "cultural_summary": context_result.get("cultural_summary", ""),
            "coordinates": context_result.get("coordinates", {}),
            "verified": context_result.get("verified", False),
            "certainty": context_result.get("certainty", 0.0),
            "timestamp": context_result.get("timestamp", datetime.utcnow().isoformat()),
            "perception_data": context_result.get("perception_data", {}),
            "geo_context": context_result.get("geo_context", {})
        }
        
        # Store in Firebase Firestore
        from services.db_service import save_cultural_summary
        
        # Save to Firestore
        save_cultural_summary(user_id, session_id, cultural_data)
        
        print(f"✅ Cultural summary stored in Firebase for user {user_id}, session {session_id}")
        
        return {
            "success": True,
            "message": "Cultural summary stored successfully",
            "data": cultural_data
        }
        
    except Exception as e:
        print(f"❌ Database storage error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to store cultural summary"
        }


async def create_journal_entry(context_result: dict, user_id: str, session_id: str) -> dict:
    """Create journal entry using the journal route after context agent completes."""
    try:
        print("📖 Creating journal entry via journal route...")
        
        # Wait a few seconds as requested
        await asyncio.sleep(2)
        
        # Prepare journal entry data
        cultural_summary = context_result.get("cultural_summary", "")
        entity = context_result.get("entity", "Unknown Entity")
        coordinates = context_result.get("coordinates", {})
        
        # Create a comprehensive summary for the journal
        journal_summary = f"Cultural Discovery: {entity}\n\n"
        journal_summary += f"Location: {coordinates.get('lat', 'Unknown')}, {coordinates.get('lng', 'Unknown')}\n\n"
        journal_summary += f"Summary: {cultural_summary}\n\n"
        journal_summary += f"Discovered through AI cultural analysis and image recognition."
        
        # Prepare journal entry request
        journal_entry = {
            "photo_url": "placeholder_image_url",  # You can replace with actual image URL
            "summary": journal_summary,
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "entity": entity,
            "coordinates": coordinates,
            "cultural_notes": context_result.get("perception_data", {}).get("cultural_notes", [])
        }
        
        # Call journal route to save entry
        try:
            # Import journal service
            from services.db_service import save_journal_entry
            
            # Save journal entry
            save_journal_entry(user_id, journal_entry)
            
            print(f"✅ Journal entry created successfully for {entity}")
            
            return {
                "success": True,
                "message": "Journal entry created successfully",
                "journal_data": journal_entry
            }
            
        except Exception as journal_error:
            print(f"⚠️ Journal route error: {journal_error}")
            # Don't fail the entire process if journal creation fails
            return {
                "success": False,
                "error": str(journal_error),
                "message": "Journal entry creation failed, but continuing with response"
            }
        
    except Exception as e:
        print(f"❌ Journal creation error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to create journal entry"
        }

