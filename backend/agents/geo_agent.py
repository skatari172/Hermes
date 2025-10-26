# agents/geo_agent.py
from google.adk.agents.llm_agent import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import AgentCard
import httpx, math, time, anyio
import base64
from PIL import Image
from PIL.ExifTags import TAGS
from io import BytesIO

# Import standalone GPS extraction utility
from utils.gps_extractor import extract_gps_from_image as standalone_extract_gps


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

_cache = {}

def _get_cache(k, ttl=600):
    v = _cache.get(k)
    if v and time.time() - v["ts"] < ttl:
        return v["val"]
    if v:
        _cache.pop(k, None)
    return None

def _set_cache(k, val):
    _cache[k] = {"val": val, "ts": time.time()}

def _haversine(lat1, lon1, lat2, lon2):
    """Return distance (m) between two coordinates."""
    R = 6371000
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ, dλ = φ2 - φ1, math.radians(lon2 - lon1)
    a = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
    return 2 * R * math.asin(math.sqrt(a))

async def _reverse(lat, lng):
    key = f"rev:{lat:.5f},{lng:.5f}"
    if (v := _get_cache(key)): return v
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"format": "jsonv2", "lat": lat, "lon": lng, "zoom": 14, "addressdetails": 1}
    headers = {"User-Agent": "Hermes/1.0 (edu)"}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, params=params, headers=headers)
            r.raise_for_status()
            data = r.json()
        _set_cache(key, data)
        return data
    except Exception as e:
        print(f"⚠️ Reverse geocoding error: {e}")
        return {"display_name": "Unknown location", "error": str(e)}

async def _wiki_geo(lat, lng, radius, lang="en"):
    key = f"geo:{lang}:{lat:.5f},{lng:.5f}:{radius}"
    if (v := _get_cache(key)): return v
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query", "list": "geosearch",
        "gscoord": f"{lat}|{lng}", "gsradius": min(radius, 10000),
        "gslimit": 15, "format": "json"
    }
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, params=params)
            r.raise_for_status()
            data = r.json().get("query", {}).get("geosearch", [])
        for d in data:
            d["distance_m"] = _haversine(lat, lng, d["lat"], d["lon"])
        _set_cache(key, data)
        return data
    except Exception as e:
        print(f"⚠️ Wikipedia geosearch error: {e}")
        return []

def get_geo_context(lat: float, lng: float, radiusMeters: int = 1500, lang: str = "en") -> dict:
    """Return address + nearby landmarks with distance (m)."""
    try:
        place = anyio.run(_reverse, lat, lng)
        landmarks = anyio.run(_wiki_geo, lat, lng, radiusMeters, lang)
        return {
            "address": place.get("display_name", "Unknown location"),
            "coords": {"lat": lat, "lng": lng},
            "landmarks": [
                {"title": lm["title"], "distance_m": round(lm["distance_m"], 1)}
                for lm in landmarks
            ],
            "error": place.get("error")  # Include any errors
        }
    except Exception as e:
        print(f"⚠️ Geo context error: {e}")
        return {
            "address": "Unknown location",
            "coords": {"lat": lat, "lng": lng},
            "landmarks": [],
            "error": str(e)
        }

def get_user_location_from_api() -> dict:
    """Get user's current location from location API."""
    try:
        print("🌐 Getting user location from API...")
        
        # Call location API to get user's current location
        import httpx
        
        # Using a free IP geolocation API as an example
        # You can replace this with your preferred location API
        response = httpx.get("http://ip-api.com/json/", timeout=10)
        
        if response.status_code == 200:
            location_data = response.json()
            
            if location_data.get("status") == "success":
                lat = location_data.get("lat")
                lng = location_data.get("lon")
                city = location_data.get("city", "Unknown")
                country = location_data.get("country", "Unknown")
                
                print(f"✅ User location determined: {city}, {country}")
                print(f"📍 Coordinates: {lat}, {lng}")
                
                return {
                    "success": True,
                    "coordinates": {"lat": lat, "lng": lng},
                    "location": f"{city}, {country}",
                    "method": "location_api",
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "error": f"Location API returned error: {location_data.get('message', 'Unknown error')}",
                    "coordinates": None
                }
        else:
            return {
                "success": False,
                "error": f"Location API request failed: HTTP {response.status_code}",
                "coordinates": None
            }
            
    except Exception as e:
        print(f"❌ Location API error: {e}")
        return {
            "success": False,
            "error": f"Location API call failed: {str(e)}",
            "coordinates": None
        }

def process_image_location(image_data: str, image_format: str = "base64", radiusMeters: int = 1500, lang: str = "en") -> dict:
    """Extract GPS coordinates from image and get comprehensive location context."""
    try:
        print("📍 Extracting GPS coordinates from image...")
        
        # First try to extract GPS from EXIF data
        gps_result = standalone_extract_gps(image_data, image_format)
        
        if gps_result["success"]:
            coordinates = gps_result["coordinates"]
            lat = coordinates["lat"]
            lng = coordinates["lng"]
            
            print(f"✅ GPS coordinates extracted from EXIF: {lat}, {lng}")
            
            # Get location context using extracted coordinates
            print("🗺️ Getting location context...")
            location_context = get_geo_context(lat, lng, radiusMeters, lang)
            
            return {
                "success": True,
                "gps_extraction": gps_result,
                "location_context": location_context,
                "coordinates": coordinates,
                "method": "exif_gps",
                "error": None
            }
        else:
            print(f"⚠️ No GPS data in EXIF: {gps_result['error']}")
            print("🌐 Falling back to user location API...")
            
            # Fallback: Get user's current location from API
            location_result = get_user_location_from_api()
            
            if location_result["success"]:
                coordinates = location_result["coordinates"]
                lat = coordinates["lat"]
                lng = coordinates["lng"]
                
                print(f"✅ User location determined from API: {location_result['location']}")
                print(f"📍 Coordinates: {lat}, {lng}")
                
                # Get location context using user's location
                print("🗺️ Getting location context...")
                location_context = get_geo_context(lat, lng, radiusMeters, lang)
                
                return {
                    "success": True,
                    "gps_extraction": gps_result,
                    "location_api": location_result,
                    "location_context": location_context,
                    "coordinates": coordinates,
                    "method": "location_api",
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "error": f"Could not determine location: {location_result['error']}",
                    "gps_extraction": gps_result,
                    "location_api": location_result,
                    "location_context": None
                }
        
    except Exception as e:
        print(f"❌ Image location processing error: {e}")
        return {
            "success": False,
            "error": f"Image location processing failed: {str(e)}",
            "gps_extraction": None,
            "location_context": None
        }

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="geo_agent",
    description="Extracts GPS coordinates from images and provides comprehensive geolocation context including addresses, nearby landmarks, and cultural sites.",
    instruction="""You are the Geo Agent in the Hermes AI travel companion system. Your role is to:

**Core Tasks:**
1. **GPS Extraction**: Extract GPS coordinates from image EXIF data
2. **Reverse Geocoding**: Convert coordinates to human-readable addresses
3. **Landmark Discovery**: Find nearby cultural sites, monuments, and points of interest
4. **Cultural Context**: Provide cultural significance of locations
5. **Error Handling**: Gracefully handle API failures and provide fallback information

**Tools Available:**
- `extract_gps_from_image`: Extract GPS coordinates from image EXIF data
- `get_geo_context`: Get comprehensive location context including address and nearby landmarks
- `process_image_location`: Complete workflow - extract GPS from image and get location context

**Workflow:**
1. When given an image, first try to extract GPS coordinates from EXIF data
2. Use extracted coordinates to get reverse geocoding and nearby landmarks
3. Provide comprehensive location context including cultural sites
4. Handle cases where GPS data is not available gracefully

**Output Format:**
Always provide structured data with:
- success: Boolean indicating if operation succeeded
- coordinates: Extracted GPS coordinates (lat, lng)
- address: Human-readable location description
- landmarks: List of nearby cultural sites with titles and distances
- error handling: Graceful fallbacks when APIs fail

**Important:** Always include error handling and provide useful information even when external APIs fail or GPS data is unavailable.""",
    tools=[extract_gps_from_image, get_geo_context, process_image_location],
)

a2a_app = to_a2a(
    root_agent,
    port=8001,
    agent_card=AgentCard(
        name="geo_agent",
        url="http://localhost:8001",
        description="Extracts GPS coordinates from images and provides comprehensive geolocation context via OSM & Wikipedia GeoSearch with error handling.",
        version="1.3.0",
        defaultInputModes=["application/json"],
        defaultOutputModes=["application/json"],
    ),
)
