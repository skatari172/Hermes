"""
Standalone geo utilities using Wikipedia and OpenStreetMap.
No ADK dependencies - can be imported without a2a issues.
"""
import httpx
import math
import time
import anyio

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

async def get_geo_context_async(lat: float, lng: float, radiusMeters: int = 1500, lang: str = "en") -> dict:
    """Async version - Return address + nearby landmarks with distance (m)."""
    try:
        place = await _reverse(lat, lng)
        landmarks = await _wiki_geo(lat, lng, radiusMeters, lang)
        address = place.get("display_name", "Unknown location")
        
        # Extract city from address components if available
        city = "Unknown City"
        if "address" in place:
            city = place["address"].get("city", place["address"].get("town", "Unknown City"))
        
        return {
            "address": address,
            "city": city,
            "country": place.get("address", {}).get("country", "Unknown Country"),
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
            "city": "Unknown City",
            "country": "Unknown Country",
            "coords": {"lat": lat, "lng": lng},
            "landmarks": [],
            "error": str(e)
        }

def get_geo_context(lat: float, lng: float, radiusMeters: int = 1500, lang: str = "en") -> dict:
    """Sync wrapper that calls async version. Returns address + nearby landmarks with distance (m)."""
    return anyio.run(get_geo_context_async, lat, lng, radiusMeters, lang)

