# agents/wiki_agent.py
from google.adk.agents.llm_agent import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import AgentCard
import httpx, urllib.parse, anyio

async def _search_page(title: str, lang="en"):
    """Search Wikipedia for a page mentioning the title and return the top result."""
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query", "list": "search", "srsearch": title,
        "format": "json", "srlimit": 1
    }
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(url, params=params)
        r.raise_for_status()
        hits = r.json().get("query", {}).get("search", [])
        if not hits:
            return None
        return hits[0]["title"]

async def _summary(title: str, lang="en"):
    """Return page summary; fallback to search if exact title not found."""
    encoded = urllib.parse.quote(title.replace(" ", "_"))
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
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
        return data

def get_wiki_context(titles: list[str], lang: str = "en") -> dict:
    """Fetch summaries for a list of titles with fallback + mention detection."""
    results = []
    for t in titles:
        s = anyio.run(_summary, t, lang)
        if s:
            results.append({
                "requested_title": t,
                "page_title": s.get("title"),
                "extract": s.get("extract"),
                "url": s.get("content_urls", {}).get("desktop", {}).get("page"),
                "mention_found": s.get("mention_found", False)
            })
    return {"facts": results}

root_agent = Agent(
    model="gemini-2.5-flash",
    name="wiki_agent",
    description="Fetches cultural and historical facts from Wikipedia with search fallback.",
    instruction="Use get_wiki_context with entity names to retrieve verified summaries.",
    tools=[get_wiki_context],
)

a2a_app = to_a2a(
    root_agent,
    port=8002,
    agent_card=AgentCard(
        name="wiki_agent",
        url="http://localhost:8002",
        description="Wikipedia summaries for entities, with mention detection.",
        version="1.1.0",
        defaultInputModes=["application/json"],
        defaultOutputModes=["application/json"],
    ),
)
