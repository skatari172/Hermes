# TODO: Gemini Vision (image understanding + OCR)
# agents/perception_agent.py
import json
import base64
import io
import re
from typing import List, Dict, Any
from PIL import Image
import httpx

from google.adk.agents.llm_agent import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import AgentCard
from google.genai import GenerativeModel


def analyze_image_perception(image_data: str, image_format: str = "base64") -> Dict[str, Any]:
    """
    Analyze an image to extract visual understanding, text recognition, and cultural cues.

    Args:
        image_data: Base64 encoded image data or image URL
        image_format: "base64" or "url"

    Returns:
        JSON structure with scene analysis, detected objects, text analysis, and cultural notes
    """

    model = GenerativeModel("gemini-2.5-flash-image")

    # Load image bytes
    try:
        if image_format == "url":
            with httpx.Client(timeout=10) as client:
                response = client.get(image_data)
                response.raise_for_status()
                image_bytes = response.content
        else:
            image_bytes = base64.b64decode(image_data)
    except Exception as e:
        return {
            "error": f"Failed to retrieve image: {str(e)}",
            "scene_summary": "Unable to analyze image",
            "detected_objects": [],
            "text_analysis": [],
            "cultural_notes": [],
            "observational_metadata": {
                "time_of_day": "unclear",
                "weather_conditions": "unclear",
            },
            "translation_summary": "No text detected due to image retrieval error",
        }

    # Load the image using Pillow
    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        return {
            "error": f"Failed to load image: {str(e)}",
            "scene_summary": "Unable to analyze image",
            "detected_objects": [],
            "text_analysis": [],
            "cultural_notes": [],
            "observational_metadata": {
                "time_of_day": "unclear",
                "weather_conditions": "unclear",
            },
            "translation_summary": "No text detected due to image loading error",
        }

    # Define the perception prompt
    prompt = """
    You are the Perception Agent in the Hermes AI travel companion system. Analyze this image and provide a comprehensive visual understanding.

    Tasks:
    1. **Visual Understanding**: Identify visible structures, objects, people, natural features, or symbols. Describe colors, shapes, and patterns.
    2. **Text Recognition & Translation**: 
       - Detect ALL visible text (OCR) - signs, menus, street names, building names, etc.
       - Identify the language of each detected text
       - Translate non-English text to English
       - If text is already in English, set translation to the same text
       - Include confidence level for each translation
    3. **Cultural or Historical Cues**: Describe cultural, artistic, or architectural styles neutrally.
    4. **Environmental Context**: Note time of day, weather, and scene characteristics.

    IMPORTANT: For foreign text translation:
    - Always provide both original text and English translation
    - Include context about what the text appears to be (sign, menu, street name, etc.)
    - If you're unsure about translation accuracy, note it in the confidence field

    Respond in this exact JSON format:
    {
        "scene_summary": "...",
        "detected_objects": [
            {"name": "...", "category": "...", "description": "..."}
        ],
        "text_analysis": [
            {
                "detected_text": "...",
                "language": "...",
                "translation": "...",
                "confidence": 0.95,
                "context": "street sign/menu/building name/etc"
            }
        ],
        "cultural_notes": ["..."],
        "observational_metadata": {
            "time_of_day": "...",
            "weather_conditions": "..."
        },
        "translation_summary": "Summary of any foreign text found and translated"
    }
    """

    try:
        response = model.generate_content([prompt, image])

        # Attempt to parse structured JSON from model output
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {
                    "scene_summary": response.text[:200] + "..."
                    if len(response.text) > 200
                    else response.text,
                    "detected_objects": [],
                    "text_analysis": [],
                    "cultural_notes": [],
                    "observational_metadata": {
                        "time_of_day": "unclear",
                        "weather_conditions": "unclear",
                    },
                    "translation_summary": "Text analysis failed - unable to parse structured response",
                }

        return result

    except Exception as e:
        return {
            "error": f"Failed to analyze image: {str(e)}",
            "scene_summary": "Unable to analyze image due to processing error",
            "detected_objects": [],
            "text_analysis": [],
            "cultural_notes": [],
            "observational_metadata": {
                "time_of_day": "unclear",
                "weather_conditions": "unclear",
            },
            "translation_summary": "No text detected due to analysis error",
        }


def extract_translations_for_user(perception_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and format translations for user display.
    This ensures foreign text translations are properly highlighted for the user.
    
    Args:
        perception_result: Result from analyze_image_perception
        
    Returns:
        Formatted translation information for user display
    """
    try:
        text_analysis = perception_result.get("text_analysis", [])
        foreign_texts = []
        english_texts = []
        
        for text_item in text_analysis:
            detected_text = text_item.get("detected_text", "")
            language = text_item.get("language", "unknown")
            translation = text_item.get("translation", "")
            context = text_item.get("context", "text")
            confidence = text_item.get("confidence", 0.0)
            
            if language.lower() != "english" and translation:
                foreign_texts.append({
                    "original": detected_text,
                    "language": language,
                    "translation": translation,
                    "context": context,
                    "confidence": confidence
                })
            elif language.lower() == "english":
                english_texts.append({
                    "text": detected_text,
                    "context": context
                })
        
        return {
            "has_foreign_text": len(foreign_texts) > 0,
            "foreign_translations": foreign_texts,
            "english_texts": english_texts,
            "translation_summary": perception_result.get("translation_summary", ""),
            "total_text_items": len(text_analysis)
        }
        
    except Exception as e:
        print(f"⚠️ Translation extraction error: {e}")
        return {
            "has_foreign_text": False,
            "foreign_translations": [],
            "english_texts": [],
            "translation_summary": "Translation extraction failed",
            "total_text_items": 0
        }


# Define root perception agent
root_agent = LlmAgent(
    model="gemini-2.5-flash-image",
    name="perception_agent",
    description=(
        "Observes and describes what is visible in images captured by travelers, "
        "including objects, text recognition, cultural analysis, and foreign text translation."
    ),
    instruction="""You are the Perception Agent in the Hermes AI travel companion system. Your role is to:

**Core Tasks:**
1. **Visual Understanding**: Identify visible structures, objects, people, natural features, or symbols. Describe colors, shapes, and patterns.
2. **Text Recognition & Translation**: 
   - Detect ALL visible text (OCR) - signs, menus, street names, building names, etc.
   - Identify the language of each detected text
   - Translate non-English text to English
   - Include confidence level for each translation
3. **Cultural Analysis**: Describe cultural, artistic, or architectural styles neutrally.
4. **Environmental Context**: Note time of day, weather, and scene characteristics.

**Tools Available:**
- `analyze_image_perception`: Analyze images and extract structured visual insights
- `extract_translations_for_user`: Format foreign text translations for user display

**Output Format:**
Always respond with structured JSON containing:
- scene_summary: Overall description of what's visible
- detected_objects: List of objects with name, category, description
- text_analysis: List of text with original, language, translation, confidence, context
- cultural_notes: List of cultural observations
- observational_metadata: Time of day, weather conditions
- translation_summary: Summary of any foreign text found and translated

**Important:** For foreign text translation, always provide both original text and English translation with confidence levels.""",
    tools=[analyze_image_perception, extract_translations_for_user],
)

# Expose agent via A2A protocol for interoperability
a2a_app = to_a2a(
    root_agent,
    port=8004,
    agent_card=AgentCard(
        name="perception_agent",
        url="http://localhost:8004",
        description="Analyzes images for objects, text recognition, cultural context, and foreign text translation.",
        version="1.0.0",
        defaultInputModes=["application/json"],
        defaultOutputModes=["application/json"],
        capabilities={},
        skills=[
            {
                "id": "image_analysis",
                "name": "Image Perception Analysis",
                "description": (
                    "Analyzes images to extract visual understanding, OCR, cultural insights, and foreign text translation."
                ),
                "tags": ["vision", "ocr", "culture", "perception", "translation"],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
            }
        ],
    ),
)
