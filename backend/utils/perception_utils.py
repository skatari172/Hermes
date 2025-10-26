"""
Perception Agent Utilities
Standalone functions for image analysis with translation priority
"""
import os
import json
import base64
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()


async def analyze_image_with_translation(image_data: str, image_format: str = "base64") -> dict:
    """Analyze image with priority on OCR and translation."""
    try:
        print("🔍 Analyzing image with OCR and translation priority...")
        
        # Use Gemini for image analysis with translation focus
        from google.generativeai import GenerativeModel
        import google.generativeai as genai
        
        # Configure API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not found in environment variables")
            return {
                "success": False,
                "error": "Google API key not configured",
                "scene_summary": "Unable to analyze image - API key missing",
                "translated_text": [],
                "cultural_landmarks": [],
                "architectural_style": "",
                "cultural_elements": [],
                "atmosphere": "",
                "cultural_notes": []
            }
        
        genai.configure(api_key=api_key)
        model = GenerativeModel("gemini-2.5-flash")
        
        # Handle different image formats
        if image_format == "base64":
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data
        
        # Create image object
        image = Image.open(BytesIO(image_bytes))
        
        # Prompt that prioritizes translation
        prompt = """Analyze this image with special focus on text translation and cultural context. 

PRIORITY ORDER:
1. TRANSLATE any foreign text you see (signs, menus, documents, etc.)
2. Identify cultural landmarks, monuments, or significant buildings
3. Analyze architectural styles and cultural elements
4. Note any religious, historical, or cultural symbols
5. Describe the scene and atmosphere

Provide your analysis in this JSON format:
{
    "scene_summary": "Brief description of what you see",
    "translated_text": [
        {"original": "foreign text", "translation": "English translation", "language": "detected language"},
        {"original": "more text", "translation": "translation", "language": "language"}
    ],
    "cultural_landmarks": ["list of landmarks or cultural sites"],
    "architectural_style": "description of building styles",
    "cultural_elements": ["religious symbols", "cultural artifacts", "etc"],
    "atmosphere": "description of the scene's cultural atmosphere",
    "cultural_notes": ["interesting cultural observations"]
}

Focus heavily on translating any text you see!"""
        
        response = model.generate_content([prompt, image])
        response_text = response.text.strip()
        
        # Try to parse JSON response
        try:
            analysis_data = json.loads(response_text)
            print(f"✅ Image analysis complete with {len(analysis_data.get('translated_text', []))} translations")
            return {
                "success": True,
                "scene_summary": analysis_data.get("scene_summary", ""),
                "translated_text": analysis_data.get("translated_text", []),
                "cultural_landmarks": analysis_data.get("cultural_landmarks", []),
                "architectural_style": analysis_data.get("architectural_style", ""),
                "cultural_elements": analysis_data.get("cultural_elements", []),
                "atmosphere": analysis_data.get("atmosphere", ""),
                "cultural_notes": analysis_data.get("cultural_notes", [])
            }
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "success": True,
                "scene_summary": response_text[:200] + "...",
                "translated_text": [],
                "cultural_landmarks": [],
                "architectural_style": "",
                "cultural_elements": [],
                "atmosphere": "",
                "cultural_notes": []
            }
        
    except Exception as e:
        print(f"❌ Image analysis error: {e}")
        return {
            "success": False,
            "error": f"Image analysis failed: {str(e)}",
            "scene_summary": "Unable to analyze image",
            "translated_text": [],
            "cultural_landmarks": [],
            "architectural_style": "",
            "cultural_elements": [],
            "atmosphere": "",
            "cultural_notes": []
        }

