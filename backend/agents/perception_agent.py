# TODO: Gemini Vision (image understanding + OCR)
# agents/perception_agent.py
import json
import base64
import io
import re
from typing import List, Dict, Any
from PIL import Image
import httpx

from google.adk.agents.llm_agent import Agent
from google.adk.a2a import to_a2a
from google.adk.a2a.types import AgentCard
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
        }

    # Define the perception prompt
    prompt = """
    You are the Perception Agent in the Hermes AI travel companion system. Analyze this image and provide a comprehensive visual understanding.

    Tasks:
    1. **Visual Understanding**: Identify visible structures, objects, people, natural features, or symbols. Describe colors, shapes, and patterns.
    2. **Text Recognition & Translation**: Detect all visible text (OCR). Identify the language of each detected text. Translate non-English text to English inline.
    3. **Cultural or Historical Cues**: Describe cultural, artistic, or architectural styles neutrally.
    4. **Environmental Context**: Note time of day, weather, and scene characteristics.

    Respond in this exact JSON format:
    {
        "scene_summary": "...",
        "detected_objects": [
            {"name": "...", "category": "...", "description": "..."}
        ],
        "text_analysis": [
            {"detected_text": "...", "language": "...", "translation": "..."}
        ],
        "cultural_notes": ["..."],
        "observational_metadata": {
            "time_of_day": "...",
            "weather_conditions": "..."
        }
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
        }


# Define root perception agent
root_agent = Agent(
    model="gemini-2.5-flash-image",
    name="perception_agent",
    description=(
        "Observes and describes what is visible in images captured by travelers, "
        "including objects, text recognition, and cultural analysis."
    ),
    instruction=(
        "Use analyze_image_perception to analyze images and extract structured visual insights."
    ),
    tools=[analyze_image_perception],
)

# Expose agent via A2A protocol for interoperability
a2a_app = to_a2a(
    root_agent,
    port=8004,
    agent_card=AgentCard(
        name="perception_agent",
        url="http://localhost:8004",
        description="Analyzes images for objects, text, and cultural context.",
        version="1.0.0",
        defaultInputModes=["application/json"],
        defaultOutputModes=["application/json"],
        capabilities={},
        skills=[
            {
                "id": "image_analysis",
                "name": "Image Perception Analysis",
                "description": (
                    "Analyzes images to extract visual understanding, OCR, and cultural insights."
                ),
                "tags": ["vision", "ocr", "culture", "perception"],
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
            }
        ],
    ),
)
