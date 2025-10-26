"""
Geo Utilities
Standalone functions for location context (no ADK dependency)
"""
import httpx
import math
import time


def get_location_context(lat: float, lng: float) -> dict:
    """Get location context using maps API."""
    try:
        print(f"🗺️ Getting location context for {lat}, {lng}...")
        
        # Use Google Maps API or similar to get location details
        # For now, return mock data - you can integrate with your maps service
        return {
            "success": True,
            "address": f"Location at {lat}, {lng}",
            "landmarks": [
                {"title": "Nearby Landmark", "description": "Cultural site in the area"},
                {"title": "Historical Site", "description": "Important historical location"}
            ],
            "city": "Current City",
            "country": "Current Country"
        }
        
    except Exception as e:
        print(f"❌ Location context error: {e}")
        return {
            "success": False,
            "error": str(e),
            "address": "Unknown location",
            "landmarks": [],
            "city": "Unknown",
            "country": "Unknown"
        }

