# agents/geo_agent.py
from google.adk.agents.llm_agent import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import AgentCard
import httpx, math, time, anyio

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

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="geo_agent",
    description="Provides geolocation context including addresses, nearby landmarks, and cultural sites.",
    instruction="""You are the Geo Agent in the Hermes AI travel companion system. Your role is to:

**Core Tasks:**
1. **Reverse Geocoding**: Convert coordinates to human-readable addresses
2. **Landmark Discovery**: Find nearby cultural sites, monuments, and points of interest
3. **Cultural Context**: Provide cultural significance of locations
4. **Error Handling**: Gracefully handle API failures and provide fallback information

**Tools Available:**
- `get_geo_context`: Get comprehensive location context including address and nearby landmarks

**Output Format:**
Always provide structured data with:
- address: Human-readable location description
- coords: Original coordinates
- landmarks: List of nearby cultural sites with titles and descriptions
- error handling: Graceful fallbacks when APIs fail

**Important:** Always include error handling and provide useful information even when external APIs fail.""",
    tools=[get_geo_context],
)

a2a_app = to_a2a(
    root_agent,
    port=8001,
    agent_card=AgentCard(
        name="geo_agent",
        url="http://localhost:8001",
        description="Reverse-geocode + nearby landmarks via OSM & Wikipedia GeoSearch with error handling.",
        version="1.2.0",
        defaultInputModes=["application/json"],
        defaultOutputModes=["application/json"],
    ),
)
