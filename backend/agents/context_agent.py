# agents/context_agent.py
import json, httpx, tempfile
from PIL import Image
from google.adk.agents.llm_agent import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.genai import GenerativeModel
from a2a.types import AgentCard

# Remote agent references
GEO_CARD_URL  = f"http://localhost:8001{AGENT_CARD_WELL_KNOWN_PATH}"
WIKI_CARD_URL = f"http://localhost:8002{AGENT_CARD_WELL_KNOWN_PATH}"

geo_agent  = RemoteA2aAgent(name="geo_agent_remote",  agent_card_url=GEO_CARD_URL)
wiki_agent = RemoteA2aAgent(name="wiki_agent_remote", agent_card_url=WIKI_CARD_URL)

def build_context(lat: float, lng: float, perception_clues: dict,
                  image_url: str | None = None, radiusMeters: int = 1500, lang: str = "en") -> dict:
    """
    Build verified context from image + geo data.
    - Uses Gemini 2.5 Flash Image to confirm entity identity (>90% confidence).
    - Calls geo_agent for nearby context and wiki_agent for enrichment only if sure.
    """
    # Step 1: gather geolocation context
    geo = geo_agent.run_tool("get_geo_context", {"lat": lat, "lng": lng, "radiusMeters": radiusMeters, "lang": lang})

    # Step 2: verify what entity is shown using Gemini multimodal
    model = GenerativeModel("gemini-2.5-flash-image")

    clues_str = json.dumps(perception_clues, ensure_ascii=False)
    prompt = f"""
    You are a fact-verification agent.
    Clues from perception: {clues_str}
    Location: ({lat}, {lng})
    Decide if this image shows a real-world entity (building, person, artwork, etc.)
    that has public information online (Wikipedia, Wikidata, Google Knowledge Graph).
    Rules:
    - Only return an entity if you are certain (>90% confidence).
    - If uncertain, respond with entity=null.
    Output JSON strictly in this format:
    {{
      "entity": string or null,
      "entity_type": "building" | "person" | "organization" | "artwork" | "object" | null,
      "certainty": float,
      "reason": string
    }}
    """

    # load image
    if image_url:
        img_path = tempfile.mktemp(suffix=".jpg")
        try:
            with httpx.Client(timeout=10) as c, open(img_path, "wb") as f:
                r = c.get(image_url)
                f.write(r.content)
            image = Image.open(img_path)
        except Exception as e:
            print("⚠️ Error loading image:", e)
            image = None
    else:
        image = None

    content = [prompt, image] if image else [prompt]
    resp = model.generate_content(content)
    try:
        result = json.loads(resp.text)
    except Exception:
        result = {"entity": None, "reason": "Failed to parse Gemini output"}

    # Step 3: Only call wiki_agent if certain and entity exists
    facts = []
    if result.get("entity") and result.get("certainty", 0) >= 0.9:
        wiki = wiki_agent.run_tool("get_wiki_context", {"titles": [result["entity"]], "lang": lang})
        facts = wiki.get("facts", [])

    return {
        "verified": bool(result.get("entity") and facts),
        "entity": result.get("entity"),
        "entity_type": result.get("entity_type"),
        "certainty": result.get("certainty"),
        "reason": result.get("reason"),
        "geo": geo,
        "facts": facts,
    }

root_agent = Agent(
    model="gemini-2.5-flash-image",
    name="context_agent",
    description="Identifies and verifies real-world entities from image + geo + perception data.",
    instruction="Use build_context to combine perception clues, image, and location; research only if certain.",
    tools=[build_context],
)

a2a_app = to_a2a(
    root_agent,
    port=8003,
    agent_card=AgentCard(
        name="context_agent",
        url="http://localhost:8003",
        description="Verifies entities using Gemini multimodal reasoning, then enriches via geo/wiki agents.",
        version="2.0.0",
        defaultInputModes=["application/json"],
        defaultOutputModes=["application/json"],
    ),
)
