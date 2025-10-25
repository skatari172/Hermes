# wiki_layer.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict
import httpx, urllib.parse  # pyright: ignore[reportMissingImports]

router = APIRouter(prefix="/context", tags=["Wikipedia Context"])

class Landmark(BaseModel):
    title: str
    distance_m: Optional[float] = None

class WikiRequest(BaseModel):
    lang: str = "en"
    landmarks: List[Landmark]
    perceptionKeywords: Optional[List[str]] = None
    ocrText: Optional[str] = None

async def wiki_summary(title: str, lang="en") -> Optional[Dict]:
    encoded = urllib.parse.quote(title.replace(" ", "_"))
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        if r.status_code != 200:
            return None
        return r.json()

@router.post("/knowledge")
async def get_knowledge(req: WikiRequest):
    # Get summaries for top 5 landmarks
    top_titles = [lm.title for lm in req.landmarks][:5]
    results = []
    for title in top_titles:
        s = await wiki_summary(title, req.lang)
        if not s:
            continue
        results.append({
            "title": title,
            "summary": s.get("extract"),
            "url": s.get("content_urls", {}).get("desktop", {}).get("page"),
        })

    # Optionally merge perception keywords or OCR text
    keywords = []
    if req.perceptionKeywords:
        keywords.extend(req.perceptionKeywords)
    if req.ocrText:
        keywords.extend(req.ocrText.split())

    return {
        "facts": results,
        "keywords": keywords[:10],
        "source": "Wikipedia",
    }
