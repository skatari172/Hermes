# geo_layer.py
from fastapi import APIRouter
from pydantic import BaseModel, Field
import httpx, math, time  # pyright: ignore[reportMissingImports]
from typing import Dict, Any, List

router = APIRouter(prefix="/geo", tags=["Geolocation"])

# Simple TTL cache to prevent hitting API limits
cache = {}

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlmb/2)**2
    return 2 * R * math.asin(math.sqrt(a))

class GeoRequest(BaseModel):
    lat: float
    lng: float
    radiusMeters: int = Field(1500, ge=100, le=10000)
    lang: str = Field("en")

async def reverse_geocode(lat: float, lng: float) -> Dict[str, Any]:
    key = f"rev:{lat:.5f},{lng:.5f}"
    if key in cache and time.time() - cache[key]["ts"] < 600:
        return cache[key]["val"]

    async with httpx.AsyncClient(timeout=10) as client:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {"format": "jsonv2", "lat": lat, "lon": lng, "zoom": 14, "addressdetails": 1}
        headers = {"User-Agent": "Hermes/1.0 (educational)"}
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()
        cache[key] = {"ts": time.time(), "val": data}
        return data

async def wikipedia_geosearch(lat: float, lng: float, radius_m: int, lang="en"):
    key = f"geo:{lang}:{lat:.5f},{lng:.5f}:{radius_m}"
    if key in cache and time.time() - cache[key]["ts"] < 600:
        return cache[key]["val"]

    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query", "list": "geosearch",
        "gscoord": f"{lat}|{lng}", "gsradius": radius_m, "gslimit": 15, "format": "json"
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json().get("query", {}).get("geosearch", [])
        for d in data:
            d["distance_m"] = haversine_m(lat, lng, d["lat"], d["lon"])
        cache[key] = {"ts": time.time(), "val": data}
        return data

@router.post("/context")
async def geo_context(req: GeoRequest):
    place = await reverse_geocode(req.lat, req.lng)
    landmarks = await wikipedia_geosearch(req.lat, req.lng, req.radiusMeters, req.lang)
    return {
        "location": {
            "coords": {"lat": req.lat, "lng": req.lng},
            "address": place.get("address", {}),
            "display_name": place.get("display_name"),
        },
        "landmarks": landmarks,
    }
