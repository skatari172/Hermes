"""
Geo Utilities
Standalone functions for location context (no ADK dependency)
"""
import httpx
import math
import time


def get_location_context(lat: float, lng: float) -> dict:
    """Get location context including city, address, and nearby attractions."""
    try:
        print(f"🗺️ Getting location context for {lat}, {lng}...")
        
        import httpx
        import os
        
        # Try to get location from reverse geocoding API
        api_key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("MAPS_API_KEY")
        
        if api_key:
            try:
                # Use Google Maps Reverse Geocoding API
                url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={api_key}"
                response = httpx.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("results"):
                        # Extract formatted address
                        result = data["results"][0]
                        address = result.get("formatted_address", f"Location at {lat}, {lng}")
                        
                        # Extract city and country
                        city = "Unknown City"
                        country = "Unknown Country"
                        for component in result.get("address_components", []):
                            types = component.get("types", [])
                            if "locality" in types:
                                city = component.get("long_name", city)
                            elif "administrative_area_level_1" in types:
                                state = component.get("short_name", "")
                            elif "country" in types:
                                country = component.get("long_name", country)
                        
                        location_name = f"{city}, {country}"
                        print(f"✅ Location determined: {location_name}")
                        
                        return {
                            "success": True,
                            "address": address,
                            "city": city,
                            "country": country,
                            "location": location_name,
                            "landmarks": [],  # Will be populated by nearby search
                            "coordinates": {"lat": lat, "lng": lng}
                        }
            except Exception as api_error:
                print(f"⚠️ Maps API error: {api_error}")
        
        # Fallback: Use a basic reverse geocoding service
        try:
            response = httpx.get(f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json", timeout=10)
            if response.status_code == 200:
                data = response.json()
                address = data.get("display_name", f"Location at {lat}, {lng}")
                city = data.get("address", {}).get("city", data.get("address", {}).get("town", "Unknown City"))
                country = data.get("address", {}).get("country", "Unknown Country")
                
                print(f"✅ Location determined from OpenStreetMap: {city}, {country}")
                
                return {
                    "success": True,
                    "address": address,
                    "city": city,
                    "country": country,
                    "location": f"{city}, {country}",
                    "landmarks": [],
                    "coordinates": {"lat": lat, "lng": lng}
                }
        except Exception as osm_error:
            print(f"⚠️ OpenStreetMap error: {osm_error}")
        
        # Final fallback: return basic location info
        print(f"⚠️ Using fallback location data")
        return {
            "success": True,
            "address": f"Location at {lat}, {lng}",
            "city": "Current Area",
            "country": "Current Region",
            "location": "Current Area, Current Region",
            "landmarks": [],
            "coordinates": {"lat": lat, "lng": lng}
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

