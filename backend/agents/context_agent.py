# agents/context_agent.py
import json, httpx, tempfile
from PIL import Image
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.genai import GenerativeModel
from a2a.types import AgentCard

# Remote agent references
GEO_CARD_URL  = f"http://localhost:8001{AGENT_CARD_WELL_KNOWN_PATH}"
WIKI_CARD_URL = f"http://localhost:8002{AGENT_CARD_WELL_KNOWN_PATH}"
DATABASE_CARD_URL = f"http://localhost:8005{AGENT_CARD_WELL_KNOWN_PATH}"

geo_agent  = RemoteA2aAgent(name="geo_agent_remote",  agent_card_url=GEO_CARD_URL)
wiki_agent = RemoteA2aAgent(name="wiki_agent_remote", agent_card_url=WIKI_CARD_URL)
database_agent = RemoteA2aAgent(name="database_agent_remote", agent_card_url=DATABASE_CARD_URL)

def build_context(lat: float, lng: float, perception_clues: dict,
                  image_url: str | None = None, radiusMeters: int = 1500, lang: str = "en",
                  user_id: str = "demo_user", session_id: str = "demo_session") -> dict:
    """
    Build verified context from image + geo data.
    - Uses Gemini 2.5 Flash Image to confirm entity identity (>90% confidence).
    - Calls geo_agent for nearby context and wiki_agent for enrichment only if sure.
    - Automatically stores cultural summary in database.
    """
    # Step 1: gather geolocation context
    try:
        geo = geo_agent.run_tool("get_geo_context", {"lat": lat, "lng": lng, "radiusMeters": radiusMeters, "lang": lang})
    except Exception as e:
        print(f"⚠️ Geo agent error: {e}")
        geo = {"address": "Unknown location", "coords": {"lat": lat, "lng": lng}, "landmarks": [], "error": str(e)}

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
        try:
            wiki = wiki_agent.run_tool("get_wiki_context", {"titles": [result["entity"]], "lang": lang})
            facts = wiki.get("facts", [])
        except Exception as e:
            print(f"⚠️ Wiki agent error: {e}")
            facts = []

    # Step 4: Store cultural summary in database
    storage_result = None
    try:
        print("💾 Storing cultural summary in database...")
        context_data = {
            "perception": perception_clues,
            "wiki_facts": facts,
            "geo_context": geo,
            "verified": bool(result.get("entity") and facts),
            "entity": result.get("entity"),
            "entity_type": result.get("entity_type"),
            "certainty": result.get("certainty", 0.0)
        }
        
        storage_result = database_agent.run_tool(
            "store_image_cultural_summary",
            {
                "context_data": context_data,
                "user_id": user_id,
                "session_id": session_id
            }
        )
        print(f"✅ Cultural summary stored: {storage_result.get('summary_id', 'Unknown ID')}")
    except Exception as e:
        print(f"❌ Database storage error: {e}")
        storage_result = {"status": "error", "error": str(e)}

    return {
        "verified": bool(result.get("entity") and facts),
        "entity": result.get("entity"),
        "entity_type": result.get("entity_type"),
        "certainty": result.get("certainty"),
        "reason": result.get("reason"),
        "geo": geo,
        "facts": facts,
        "storage_result": storage_result,
        "cultural_summary": storage_result.get("cultural_summary") if storage_result else None
    }

root_agent = LlmAgent(
    model="gemini-2.5-flash-image",
    name="context_agent",
    description="Identifies and verifies real-world entities from image + geo + perception data and stores cultural summaries.",
    instruction="""You are the Context Agent in the Hermes AI travel companion system. Your role is to:

**Core Tasks:**
1. **Entity Verification**: Use Gemini multimodal reasoning to confirm entity identity (>90% confidence)
2. **Context Building**: Combine perception clues, image data, and location information
3. **Research Coordination**: Call geo and wiki agents only when certain about entity
4. **Database Storage**: Automatically store cultural summaries for future reference

**Tools Available:**
- `build_context`: Combine perception clues, image, and location; research only if certain; automatically store cultural summary in database

**Process Flow:**
1. Gather geolocation context from geo_agent
2. Use Gemini multimodal reasoning to verify entity identity
3. Only call wiki_agent if entity is certain (>90% confidence)
4. Store cultural summary in database automatically

**Output Format:**
Always provide structured data with:
- verified: Boolean indicating if entity was verified
- entity: Name of verified entity
- entity_type: Type of entity (building, monument, etc.)
- certainty: Confidence score (0.0-1.0)
- reason: Explanation of verification decision
- geo: Geographic context data
- facts: Cultural/historical facts from wiki
- storage_result: Database storage result
- cultural_summary: Generated cultural summary

**Important:** Only research entities when highly confident (>90%) to avoid irrelevant information.""",
    tools=[build_context],
)

a2a_app = to_a2a(
    root_agent,
    port=8003,
    agent_card=AgentCard(
        name="context_agent",
        url="http://localhost:8003",
        description="Verifies entities using Gemini multimodal reasoning, enriches via geo/wiki agents, and stores cultural summaries.",
        version="2.0.0",
        defaultInputModes=["application/json"],
        defaultOutputModes=["application/json"],
    ),
)
