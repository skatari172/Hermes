# agents/wiki_agent.py
from google.adk.agents.llm_agent import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import AgentCard
import httpx, urllib.parse, anyio, time

# Cache for better performance
_cache = {}

def _get_cache(key: str, ttl: int = 300) -> any:
    """Get cached result if still valid."""
    if key in _cache and time.time() - _cache[key]["ts"] < ttl:
        return _cache[key]["val"]
    return None

def _set_cache(key: str, val: any):
    """Cache a result with timestamp."""
    _cache[key] = {"val": val, "ts": time.time()}

def _is_culturally_relevant(extract: str) -> bool:
    """Check if Wikipedia extract contains cultural/historical information."""
    cultural_keywords = [
        "history", "historical", "culture", "cultural", "tradition", "traditional",
        "architecture", "architectural", "art", "artistic", "monument", "heritage",
        "ancient", "medieval", "century", "built", "constructed", "founded",
        "religious", "sacred", "ceremony", "festival", "custom", "practice",
        "museum", "gallery", "temple", "church", "mosque", "synagogue",
        "palace", "castle", "fortress", "ruins", "archaeological"
    ]
    extract_lower = extract.lower()
    return any(keyword in extract_lower for keyword in cultural_keywords)

def _calculate_cultural_relevance(extract: str) -> float:
    """Calculate relevance score for cultural/historical content."""
    cultural_keywords = [
        "history", "historical", "culture", "cultural", "tradition", "traditional",
        "architecture", "architectural", "art", "artistic", "monument", "heritage",
        "ancient", "medieval", "century", "built", "constructed", "founded"
    ]
    extract_lower = extract.lower()
    matches = sum(1 for keyword in cultural_keywords if keyword in extract_lower)
    return min(matches / len(cultural_keywords), 1.0)

async def _search_page(title: str, lang="en"):
    """Search Wikipedia for a page mentioning the title and return the top result."""
    cache_key = f"search:{lang}:{title}"
    cached = _get_cache(cache_key)
    if cached:
        return cached
    
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query", "list": "search", "srsearch": title,
        "format": "json", "srlimit": 1
    }
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, params=params)
            r.raise_for_status()
            hits = r.json().get("query", {}).get("search", [])
            result = hits[0]["title"] if hits else None
            _set_cache(cache_key, result)
            return result
    except Exception as e:
        print(f"⚠️ Search error for '{title}': {e}")
        return None

async def _summary(title: str, lang="en"):
    """Return page summary; fallback to search if exact title not found."""
    cache_key = f"summary:{lang}:{title}"
    cached = _get_cache(cache_key)
    if cached:
        return cached
    
    encoded = urllib.parse.quote(title.replace(" ", "_"))
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url)
            if r.status_code == 404:
                alt = await _search_page(title, lang)
                if not alt or alt.lower() == title.lower():
                    return None
                return await _summary(alt, lang)
            if r.status_code != 200:
                return None
            data = r.json()
            # Add mention flag if entity appears inside parent page text
            mention_found = title.lower() in data.get("extract", "").lower()
            data["mention_found"] = mention_found
            _set_cache(cache_key, data)
            return data
    except Exception as e:
        print(f"⚠️ Summary error for '{title}': {e}")
        return None

def get_wiki_context(titles: list[str], lang: str = "en") -> dict:
    """Enhanced Wikipedia search with historical/cultural focus."""
    results = []
    
    for t in titles:
        # Try multiple search strategies for cultural/historical content
        search_terms = [
            t,  # Original term
            f"{t} history",  # Historical context
            f"{t} culture",  # Cultural context
            f"{t} architecture",  # Architectural significance
            f"{t} heritage",  # Heritage sites
            f"{t} monument",  # Monuments
        ]
        
        best_result = None
        best_relevance = 0
        
        for term in search_terms:
            s = anyio.run(_summary, term, lang)
            if s:
                extract = s.get("extract", "")
                if _is_culturally_relevant(extract):
                    relevance = _calculate_cultural_relevance(extract)
                    if relevance > best_relevance:
                        best_result = {
                            "requested_title": t,
                            "search_term_used": term,
                            "page_title": s.get("title"),
                            "extract": extract,
                            "url": s.get("content_urls", {}).get("desktop", {}).get("page"),
                            "cultural_relevance_score": relevance,
                            "mention_found": s.get("mention_found", False),
                            "is_cultural_content": True
                        }
                        best_relevance = relevance
        
        # If no cultural content found, fallback to original search
        if not best_result:
            s = anyio.run(_summary, t, lang)
            if s:
                best_result = {
                    "requested_title": t,
                    "search_term_used": t,
                    "page_title": s.get("title"),
                    "extract": s.get("extract"),
                    "url": s.get("content_urls", {}).get("desktop", {}).get("page"),
                    "cultural_relevance_score": _calculate_cultural_relevance(s.get("extract", "")),
                    "mention_found": s.get("mention_found", False),
                    "is_cultural_content": _is_culturally_relevant(s.get("extract", ""))
                }
        
        if best_result:
            results.append(best_result)
    
    return {"facts": results}

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="wiki_agent",
    description="Fetches cultural and historical facts from Wikipedia with enhanced cultural relevance scoring.",
    instruction="""You are the Wiki Agent in the Hermes AI travel companion system. Your role is to:

**Core Tasks:**
1. **Cultural Research**: Search Wikipedia for historical and cultural information
2. **Relevance Scoring**: Prioritize culturally and historically significant content
3. **Multi-Search Strategy**: Use multiple search terms to find the best cultural context
4. **Caching**: Optimize performance with intelligent caching

**Tools Available:**
- `get_wiki_context`: Enhanced Wikipedia search with historical/cultural focus

**Search Strategy:**
For each entity, search with multiple terms:
- Original term
- "{entity} history" - Historical context
- "{entity} culture" - Cultural context  
- "{entity} architecture" - Architectural significance
- "{entity} heritage" - Heritage sites
- "{entity} monument" - Monuments

**Cultural Relevance:**
Prioritize content that mentions:
- Historical events, dates, periods
- Cultural practices, traditions, customs
- Architectural styles, artistic movements
- Heritage sites, monuments, UNESCO sites
- Cultural significance, importance

**Output Format:**
Always provide structured data with:
- requested_title: Original search term
- search_term_used: Which search term found the best result
- page_title: Wikipedia page title
- extract: Cultural/historical information
- url: Wikipedia page URL
- cultural_relevance_score: 0.0-1.0 relevance score
- is_cultural_content: Boolean indicating cultural relevance

**Important:** Focus on cultural and historical significance, not general information.""",
    tools=[get_wiki_context],
)

a2a_app = to_a2a(
    root_agent,
    port=8002,
    agent_card=AgentCard(
        name="wiki_agent",
        url="http://localhost:8002",
        description="Enhanced Wikipedia search for cultural and historical facts with relevance scoring.",
        version="1.1.0",
        defaultInputModes=["application/json"],
        defaultOutputModes=["application/json"],
    ),
)
