"""
Context Agent Utilities
Standalone functions for building comprehensive context
"""
from datetime import datetime


def build_comprehensive_context(lat: float, lng: float, perception_clues: dict, geo_context: dict, user_id: str, session_id: str) -> dict:
    """Build comprehensive context from all data sources."""
    try:
        print("🧠 Building comprehensive context...")
        
        # Check if geo_context has error
        if geo_context.get("error"):
            print(f"⚠️ Geo context has error: {geo_context.get('error')}")
        
        # Extract key information
        scene_summary = perception_clues.get("scene_summary", "")
        translated_text = perception_clues.get("translated_text", [])
        cultural_landmarks = perception_clues.get("cultural_landmarks", [])
        
        # Determine entity from landmarks or translated text
        entity = "Unknown Entity"
        if cultural_landmarks:
            entity = cultural_landmarks[0]
        elif translated_text:
            entity = translated_text[0].get("translation", "Unknown Entity")
        
        # Build cultural summary
        cultural_summary = f"Scene: {scene_summary}"
        if translated_text:
            cultural_summary += f"\n\nTranslated Text:\n"
            for text in translated_text:
                cultural_summary += f"- {text.get('original', '')} → {text.get('translation', '')} ({text.get('language', 'unknown')})\n"
        
        if cultural_landmarks:
            cultural_summary += f"\n\nCultural Landmarks: {', '.join(cultural_landmarks)}"
        
        # Log landmarks for debugging
        landmarks = geo_context.get("landmarks", [])
        if landmarks:
            print(f"📍 Found {len(landmarks)} nearby landmarks: {[lm.get('title', lm.get('name', 'Unknown')) for lm in landmarks[:3]]}")
        else:
            print("⚠️ No nearby landmarks found")
        
        # Include geo_context data directly accessible
        return {
            "success": True,
            "entity": entity,
            "entity_type": "cultural_site",
            "verified": True,
            "certainty": 0.8,
            "cultural_summary": cultural_summary,
            "coordinates": {"lat": lat, "lng": lng},
            "geo": geo_context,  # Make it accessible via .get('geo')
            "geo_context": geo_context,  # Keep for compatibility
            "location_api": geo_context,  # Also available here
            "perception_data": perception_clues,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Context building error: {e}")
        return {
            "success": False,
            "error": str(e),
            "entity": "Unknown Entity",
            "entity_type": "unknown",
            "verified": False,
            "certainty": 0.0,
            "cultural_summary": "Unable to build context",
            "coordinates": {"lat": lat, "lng": lng},
            "geo": geo_context,  # Make it accessible
            "geo_context": geo_context,
            "location_api": geo_context,
            "perception_data": perception_clues
        }

