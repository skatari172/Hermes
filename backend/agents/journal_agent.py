# agents/journal_agent.py
from google.adk.agents.llm_agent import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import AgentCard
from services.db_service import save_journal_entry, get_journal_entries
from datetime import datetime
from utils.gemini_client import gemini_client
import asyncio
import logging
import re

# -------------------------------------------------------------------
# ✅ Configure Logging
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger("journal_agent")

# -------------------------------------------------------------------
# ✅ Agent Tools
# -------------------------------------------------------------------
async def create_diary_entry(user_id: str, conversation_summary: str, photo_url: str = None) -> dict:
    """
    Create a diary entry from a conversation summary using Gemini.
    """
    try:
        logger.info(f"📝 [create_diary_entry] Called for user_id={user_id}")
        
        # Display the summary prominently in the terminal
        print("\n" + "="*80)
        print("📋 CONVERSATION SUMMARY FOR JOURNAL GENERATION")
        print("="*80)
        print(f"User ID: {user_id}")
        print(f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*80)
        print("SUMMARY:")
        print(conversation_summary)
        print("-"*80)
        print("🔄 Generating journal entry...")
        print("="*80 + "\n")
        
        logger.info(f"Conversation summary received:\n{conversation_summary}\n")

        # Fetch recent entries for context
        existing_entries = await get_journal_entries(user_id)
        recent_entries = existing_entries.get("entries", [])[-3:]
        logger.info(f"Fetched {len(recent_entries)} recent journal entries for context.")

        # Build context for Gemini
        context_parts = []
        if recent_entries:
            context_parts.append("**Recent Journal Entries:**")
            for entry in recent_entries:
                context_parts.append(f"- {entry.get('summary', 'No summary')}")
            context_parts.append("")

        context_parts.append(f"**Today's Conversation Summary:** {conversation_summary}")
        context_parts.append("")
        context_parts.append("**Instructions:**")
        context_parts.append("Transform this conversation summary into a personal, reflective diary entry.")
        context_parts.append("Write in first person, introspective and emotionally aware, in 2–3 paragraphs.")
        context_parts.append("Include insights, feelings, or reflections on what was learned or experienced.")

        prompt = "\n".join(context_parts)

        logger.debug(f"Prompt sent to Gemini:\n{prompt}\n")

        # Generate journal-style text
        diary_text = await gemini_client.generate_text(prompt)
        logger.info("✅ Gemini response received successfully.")
        
        # Remove asterisks and markdown from response
        diary_text = re.sub(r'\*\*', '', diary_text)  # Remove bold markers
        diary_text = re.sub(r'\*', '', diary_text)  # Remove any other asterisks
        diary_text = re.sub(r'#+\s*', '', diary_text)  # Remove headers
        diary_text = diary_text.strip()
        
        logger.debug(f"Generated diary entry:\n{diary_text}\n")

        # Display the generated journal entry in terminal
        print("\n" + "="*80)
        print("📖 GENERATED JOURNAL ENTRY")
        print("="*80)
        print(diary_text)
        print("="*80 + "\n")

        entry_data = {
            "photoUrl": photo_url or "",
            "diary note": diary_text,
            "timestamp": datetime.utcnow().isoformat(),
            "original_summary": conversation_summary,
            "entry_type": "diary",
        }

        # Save to Firestore
        await save_journal_entry(user_id, entry_data)
        logger.info(f"✅ Saved journal entry for user {user_id} at {entry_data['timestamp']}")
        
        print(f"✅ Journal entry saved successfully for user {user_id}")

        return {
            "success": True,
            "diary_entry": diary_text,
            "timestamp": entry_data["timestamp"],
            "message": "Diary entry created successfully",
        }

    except Exception as e:
        logger.error(f"❌ Error in create_diary_entry: {e}", exc_info=True)
        print(f"❌ Error creating journal entry: {e}")
        return {"success": False, "error": str(e), "message": "Failed to create diary entry"}

async def get_user_diary_entries(user_id: str, limit: int = 10) -> dict:
    """
    Retrieve user diary entries.
    """
    try:
        logger.info(f"📖 [get_user_diary_entries] Fetching up to {limit} entries for user_id={user_id}")
        entries = await get_journal_entries(user_id)
        diary_entries = [
            e for e in entries.get("entries", []) if e.get("entry_type") == "diary"
        ]
        diary_entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        logger.info(f"Retrieved {len(diary_entries)} diary entries for user {user_id}.")
        return {"success": True, "entries": diary_entries[:limit]}
    except Exception as e:
        logger.error(f"❌ Error in get_user_diary_entries: {e}", exc_info=True)
        return {"success": False, "error": str(e), "entries": []}

async def generate_journal_from_conversation(user_id: str, session_id: str, photo_url: str = None) -> dict:
    """
    Generate a journal entry from the current conversation summary.
    This function integrates with the conversation agent to get the latest summary.
    """
    try:
        logger.info(f"📝 [generate_journal_from_conversation] Called for user_id={user_id}, session_id={session_id}")
        
        # Import here to avoid circular imports
        from memory.summarizer import conversation_summarizer
        
        # Get the conversation summary
        conversation_summary = await conversation_summarizer.get_summary(user_id, session_id)
        
        if not conversation_summary or conversation_summary == "No conversation summary available yet.":
            print("\n" + "="*80)
            print("⚠️  NO CONVERSATION SUMMARY AVAILABLE")
            print("="*80)
            print("No conversation summary found for this session.")
            print("Please have a conversation first before generating a journal entry.")
            print("="*80 + "\n")
            
            return {
                "success": False,
                "error": "No conversation summary available",
                "message": "Please have a conversation first before generating a journal entry"
            }
        
        # Display the summary and generate journal entry
        print("\n" + "="*80)
        print("🚀 TRIGGERING JOURNAL GENERATION FROM CONVERSATION")
        print("="*80)
        print(f"User ID: {user_id}")
        print(f"Session ID: {session_id}")
        print(f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        
        # Call the create_diary_entry function with the conversation summary
        result = await create_diary_entry(user_id, conversation_summary, photo_url)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in generate_journal_from_conversation: {e}", exc_info=True)
        print(f"❌ Error generating journal from conversation: {e}")
        return {"success": False, "error": str(e), "message": "Failed to generate journal from conversation"}

# -------------------------------------------------------------------
# ✅ Google ADK Agent Definition
# -------------------------------------------------------------------
root_agent = Agent(
    model="gemini-2.5-flash",
    name="journal_agent",
    description="Creates personal diary entries from conversation summaries using Gemini.",
    instruction=(
        "Use create_diary_entry to transform conversation summaries into reflective diary entries, "
        "generate_journal_from_conversation to create entries from current conversation history, "
        "and get_user_diary_entries to fetch previous entries."
    ),
    tools=[create_diary_entry, get_user_diary_entries, generate_journal_from_conversation],
)

# -------------------------------------------------------------------
# ✅ Expose as A2A microservice for other agents
# -------------------------------------------------------------------
a2a_app = to_a2a(
    root_agent,
    port=8004,
    agent_card=AgentCard(
        name="journal_agent",
        url="http://localhost:8004",
        description="AI-powered journal entry generator that converts conversation summaries into reflective diary entries.",
        version="1.0.0",
        defaultInputModes=["application/json"],
        defaultOutputModes=["application/json"],
    ),
)

# Optional: log that the service has started
logger.info("🚀 Journal Agent initialized and running on port 8004.")

# -------------------------------------------------------------------
# ✅ Direct function for testing journal generation
# -------------------------------------------------------------------
async def test_journal_generation(user_id: str = "test_user", session_id: str = "test_session"):
    """
    Test function to generate journal entry from conversation history.
    This can be called directly for testing purposes.
    """
    print("\n" + "="*80)
    print("🧪 TESTING JOURNAL GENERATION")
    print("="*80)
    print("This function will attempt to generate a journal entry from conversation history.")
    print("="*80 + "\n")
    
    result = await generate_journal_from_conversation(user_id, session_id)
    
    if result["success"]:
        print("\n✅ Journal generation test completed successfully!")
    else:
        print(f"\n❌ Journal generation test failed: {result.get('message', 'Unknown error')}")
    
    return result

# Example usage (uncomment to test):
# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(test_journal_generation())
                                